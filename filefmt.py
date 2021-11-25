import ast, astpretty
import re
import tkinter

posMacroPattern = re.compile("((\\+|\\-)\d*)((\\+|\\-)\\d*)")

class MacroParser:
    macroPattern = re.compile("\\$[^\\$]+\\$")
    leftArgOpRe = re.compile("\+|-|/|%|\\*|<|>|\\||\\^|&|is|in|and|or|if|=|!=|\\(|\\.|\\[")

    def __init__(self):
        self.macroList = {}

    def addMacro(self, name, subs="", iconCreateFn=None):
        """Add a macro to annotate and extend the save-file and pasted-text format beyond
        the base Python syntax.  The save-file format extends Python with macros of the
        form $name:argString$.  name is composed of the same set of characters as Python
        identifiers. Macros that skip the name ($:args$) provide (mostly layout-ralated)
        information to the built-in icon creation functions for Python itself.  The colon
        separates the macro name from its arguments, and may be omitted if there are no
        arguments to pass.  The format of the argument string (argString) is entirely up
        to the implementer, but must not contain the "$" character.  The argument, subs,
        provides text to replace the macro before parsing with the Python parser, and
        may alternatively be passed as a function to generate the substitution string
        from the macro argString.  Since the ultimate goal is to create icons, string
        substitution is needed only in rare cases to temporarily support sub-structure
        (such as statement blocks) and get it to pass initial parsing.  Most of the work
        will be done in the icon creation function (iconCreateFn).  Since macros are
        associated with AST nodes based on their location in the save-file, there is
        a special case for nodes generated by text substitution by the macro, itself.
        To reference a python construct inserted by the macro, the substitution text
        should place a '$' character before the item to be marked.  The '$' will be
        removed in the substitution process, and the macro data will be associated
        with the python code that followed it in the inserted text.  iconCreateFn
        should be a function with parameters for astNode and window.  Macro name and
        macro arguments are attached to astNode as properties (macroName, macroArgs)
        (see ... for details)"""

        self.macroList[name] = subs, iconCreateFn

    def expandMacros(self, text):
        """Takes text in python_g clipboard/save-file text format, expands macros and
        returns three items:
            1) The macro-expanded text
            2) An object for looking up macro annotation (name, arguments, and icon
               creation function) given an AST node resulting from parsing the text.
            3) A list whose index is line numbers in the macro-expanded version of the
               text and whose content is the corresponding line number in the original
               text (before expansion)."""
        annotations = AnnotationList()
        lineNumTranslate = []
        origLineStarts = [0]
        origLineNum = 1
        modLineNum = 1
        modColNum = 0
        modTextFrags = []
        modFragStart = 0
        origIdx = 0
        while origIdx < len(text):
            origChar = text[origIdx]
            if origChar == '\t':
                macroFailDialog(text, origIdx, origLineNum, "Tab characters not allowed")
                return None, None, []
            if origChar == '\n':
                lineNumTranslate.append(origLineNum)
                origLineNum += 1
                modLineNum += 1
                modColNum = 0
                origLineStarts.append(origIdx+1)
                origIdx += 1
            elif origChar == '$':
                # Macro found.  Process it and get replacement text
                match = self.macroPattern.match(text, origIdx)
                if match is None:
                    macroFailDialog(text, origIdx, origLineNum)
                    return None, None, []
                macroEndIdx = origIdx + len(match.group(0))
                replaceText = self._processMacro(modLineNum, modColNum, text, origIdx,
                    macroEndIdx, annotations)
                if replaceText is None:
                    macroFailDialog(text, origIdx, origLineNum)
                    return None, None, []
                # Copy the text between the last macro and this one in to the output list
                textToCopy = text[modFragStart:origIdx]
                modTextFrags.append(textToCopy)
                # Copy the macro's replacement text in to the output list
                modTextFrags.append(replaceText)
                # Adjust line counts for newlines in macro or replaced text
                origLineNum += text[origIdx:macroEndIdx].count('\n')
                modLines = replaceText.split('\n')
                for i in range(len(modLines) - 1):
                    modLineNum += 1
                    lineNumTranslate.append(origLineNum)
                if len(modLines) > 1:
                    modColNum = len(modLines[-1])
                else:
                    modColNum += len(replaceText)
                origIdx = macroEndIdx
                modFragStart = origIdx
            else:
                modColNum += 1
                origIdx += 1
        # Copy the text between the last macro and the end of the input text to the output
        modTextFrags.append(text[modFragStart:])
        # Consolidate the output fragments in to a single string, and return it and the
        # annotation dictionary and line number translation list
        return "".join(modTextFrags), annotations, lineNumTranslate

    def _processMacro(self, modLineNum, modColNum, origText, macroStartIdx, macroEndIdx,
            annotations):
        """Process a macro in origText between macroStartIdx and macroEndIdx, adding
        entries to annotations object for associating data from the named macro and the
        argument string with appropriate AST node.  Returns text to substitute for the
        macro before passing it on to the Python parser."""
        macroText = origText[macroStartIdx+1:macroEndIdx-1]
        macroName, macroArgs = self._parseMacro(macroText)
        if macroName is None:
            return None
        if macroName == "":
            replaceText = ""
            iconFn = None
        elif macroName == "@":
            replaceText = "pass"
            iconFn = None
        else:
            macroData = self.macroList[macroName]
            if macroData is None:
                return None
            subs, iconFn, = macroData
            if callable(subs):
                replaceText = subs(macroArgs)
            else:
                replaceText = subs
        # Translate the dollar sign marker in the replacement text to an offset
        # and remove it from the text
        astMarker = replaceText.find("$")
        if astMarker == -1:
            astMarker = 0
        elif astMarker == len(replaceText) - 1:
            replaceText = replaceText[:-1]
        else:
            replaceText = replaceText[:astMarker] + replaceText[astMarker + 1:]
        # Associate the line and column of the text that will generate the AST with the
        # macro data we want to attach to it
        adjLine, adjCol = countLinesAndCols(replaceText, astMarker, modLineNum, modColNum)
        annotations.indexByStartPos(adjLine, adjCol, (macroName, macroArgs, iconFn))
        # AST nodes with arguments on the left report line and column of their leftmost
        # argument (not of their own text), which is not useful for corresponding them
        # with the text that generated them.  For binary operations and assignments
        # (and text that looks like one of these, but we can't tell without parsing)
        # record, also, the rightmost position of their left argument
        if astMarker >= len(replaceText):
            # Marked AST is after macro
            isLeftArgOp = self.leftArgOpRe.match(text, macroEndIdx)
        else:
            # Marked AST is within macro
            isLeftArgOp = self.leftArgOpRe.match(replaceText, astMarker)
        if isLeftArgOp:
            # Look backward from op through the expanded macro text to find the last
            # non-whitespace character
            adjLine, adjCol = self._leftArgLineCol(adjLine, adjCol, replaceText,
                astMarker)
            # If non-white text was not found within the macro replacement text, search
            # before the macro
            if adjLine == -1:
                adjLine, adjCol = self._leftArgLineCol(modLineNum, modColNum, origText,
                    macroStartIdx)
            annotations.indexByLeftArgEnd(adjLine, adjCol, (macroName, macroArgs, iconFn))
        return replaceText

    @staticmethod
    def _leftArgLineCol(modLineNum, modColNum, text, idx):
        """Binary operators and assignments, unfortunately, do not encode the line and
        column of the operator, but of the entire expression.  The code here, marches
        backward from the index where the operator starts (idx) to find the first
        non-white, decrementing modLineNum and modColNum per corresponding newlines and
        whitespace characters found in the string (text).  If no whitespace is found,
        returns -1 for both line and column.  The calling code will index the macro data
        by for the AST using the returned line and column, which will correspond to the
        rightmost character of its left argument."""
        for i in range(idx-1, -1, -1):
            if text[i] == '\n':
                modLineNum -= 1
                for pl in range(i-1, -1, -1):
                    if text[pl] == '\n':
                        prevLineStart = pl + 1
                        break
                else:
                    prevLineStart = 0
                modColNum = i - prevLineStart
            elif text[i] in '\t ':
                modColNum -= 1
            else:
                return modLineNum, modColNum
        return -1, -1

    @staticmethod
    def _parseMacro(macroText):
        """Split a macro into name and argument components and check for legal name.
        macroName returns None on error, and an empty string for legal but unnamed."""
        if macroText[0] == '@':
            # Segment position macro
            return '@', macroText[1:]
        if macroText[0] == ':':
            # Annotation-only for built-in Python syntax
            return "", macroText[1:]
        # Split name from arguments at :
        for i, c in enumerate(macroText):
            if c == ":":
                return macroText[:i], macroText[i+1:]
            if not c.isalnum() and c != '_':
                return None, None
        # No arguments found
        return macroText, None

class AnnotationList:
    """Associate macros with the ast nodes they generated."""
    def __init__(self):
        self.byStartPos = {}
        self.byLeftArgEnd = {}

    def indexByStartPos(self, line, col, annotation):
        self.byStartPos[(line << 16) + col] = annotation

    def indexByLeftArgEnd(self, line, col, annotation):
        self.byLeftArgEnd[(line << 16) + col] = annotation

    def get(self, node):
        leftNode = None
        nodeClass = node.__class__
        if nodeClass is ast.Expr:
            return None  # Expr nodes have the same offset as their content
        if nodeClass in (ast.BinOp, ast.Compare):
            leftNode = node.left
        elif nodeClass is ast.Assign:
            leftNode = node.targets[-1]
        elif nodeClass in (ast.AugAssign, ast.AnnAssign):
            leftNode = node.target
        elif nodeClass is ast.Call:
            leftNode = node.func
        elif nodeClass in (ast.Attribute, ast.Subscript):
            leftNode = node.value
        elif nodeClass is ast.IfExp:
            leftNode = node.body
        if leftNode:
            if hasattr(leftNode, 'end_lineno') and hasattr(leftNode, 'end_col_offset'):
                line = leftNode.end_lineno
                col = leftNode.end_col_offset
                return self.byLeftArgEnd.get((line << 16) + col)
        else:
            if hasattr(node, 'lineno') and hasattr(node, 'col_offset'):
                return self.byStartPos.get((node.lineno << 16) + node.col_offset)
        return None

    def dump(self):
        print("annotations byStartPos")
        for key, val in self.byStartPos.items():
            print("   ", key >> 16, key & 0xffff, repr(val))
        print("annotations byLeftArgEnd")
        for key, val in self.byLeftArgEnd.items():
            print("   ", key >> 16, key & 0xffff, repr(val))

def parseText(macroParser, text, fileName="Pasted Text"):
    """Parse save-file format (from clipboard or file) and return a list of tuples
    pairing a window position with a list of AST nodes to form a sequence.  If the
    position is None, the segment should be attached to the window module sequence point.
    On parse failure, posts up a dialog describing the failure and returns None."""
    # Expand macros
    expandedText, annotations, lineNumTranslate = macroParser.expandMacros(text)
    if expandedText is None:
        return None
    print('expanded Text:\n%s' % expandedText)
    print('lineNumTranslate', lineNumTranslate)
    annotations.dump()
    # Parse expanded text
    try:
        modAst = ast.parse(expandedText, fileName)
    except SyntaxError as excep:
        syntaxErrDialog(excep, lineNumTranslate, text)
        return None
    except Exception as excep:
        parseFailDialog(excep)
        return None
    if not isinstance(modAst, ast.Module) or len(modAst.body) == 0:
        print("Unexpected AST returned from ast.parse")
        return None
    # Annotate the nodes in the tree per the annotations list
    for node in ast.walk(modAst):
        ann = annotations.get(node)
        if ann is not None:
            macroName, macroArgs, iconCreateFn = ann
            if macroName is not None and macroName != "":
                node.macroName = macroName
            if macroArgs is not None:
                node.macroArgs = macroArgs
            if iconCreateFn is not None:
                node.iconCreationFunction = iconCreateFn
    # Split the parse results in to separately positioned segments
    currentSegment = []
    segments = [(None, currentSegment)]
    for node in modAst.body:
        ann = annotations.get(node)
        if ann is not None and ann[0] == "@":
            currentSegment = []
            segments.append((_parsePosMacro(ann[1]), currentSegment))
        else:
            currentSegment.append(node)
    return segments

def _parsePosMacro(macroArgs):
    match = posMacroPattern.match(macroArgs)
    if match is None:
        print("Bad format for @ (segment position) macro")
        return 0, 0
    x = int(match.group(1))
    y = int(match.group(3))
    return x,y

def loadFile(macroParser, fileName):
    with open(fileName, "r") as f:
        return parseText(macroParser, f.read(), fileName)

def syntaxErrDialog(excep, lineNumTranslate, originalText):
    caretLine = " " * (excep.offset-1) + "^"
    message = "%s: %s\n%s%s\n" % (excep.__class__.__name__,
            str(excep), excep.text, caretLine)
    origLineNum = lineNumTranslate[excep.lineno-1]
    message += "Expanded from input file line %d:\n%s" % (origLineNum,
            numberedLine(originalText, origLineNum))
    print(message)

def parseFailDialog(excep):
    message = "Parsing failed %s: %s" % (excep.__class__.__name__, str(excep))
    print(message)

def macroFailDialog(text, idx, lineNum, message=None):
    if message is None:
        macroEnd = text.find('$', idx + 1)
        if macroEnd == -1:
            macro = text[idx:idx+10] + '...'
        elif macroEnd - idx > 100:
            macro = text[idx:idx+100] + '...'
        else:
            macro = text[idx:macroEnd+1]
        message = "Unrecognized macro on line %d: %s" % (lineNum, macro)
    else:
        message = "%s, line %d" % (message, lineNum)
    for i in range(idx, -1, -1):
        if text[i] == '\n':
            lineStart = i + 1
            break
    else:
        lineStart = 0
    caretLine = " " * (idx - lineStart) + "^"
    lineEnd = text.find('\n', idx)
    if lineEnd == -1:
        lineEnd = len(text)
    lineText = text[lineStart:lineEnd]
    message += "\n%s\n%s" % (lineText, caretLine)
    print(message)

def numberedLine(text, lineNum):
    """Return a single line (lineNum) from text.  Note, that this inefficiently scans
    the entire text for newlines to find the specified line."""
    startIdx = 0
    for i in range(lineNum-1):
        startIdx = text.find('\n', startIdx)
        if startIdx == -1:
            return ""
        startIdx += 1
    endIdx = text.find('\n', startIdx)
    if endIdx == -1:
        return text[startIdx:]
    return text[startIdx:endIdx]

def countLinesAndCols(text, endPos, startLine, startCol):
    line = startLine
    col = startCol
    for i, c in enumerate(text):
        if i >= endPos:
            return line, col
        if c == '\n':
            col = 0
            line += 1
        else:
            col += 1
    return line, col

macroParser = MacroParser()
macroParser.addMacro("l1", "", countLinesAndCols)
macroParser.addMacro("testSubs", '"testing substitution"', numberedLine)
macroParser.addMacro("testDollar", 'nert.asdf$.wang.thing(wang)')
macroParser.addMacro("testDollarEnd", "3+$")
macroParser.addMacro("if", "if a == $2:\n        pass")
text="""$@-1+34$
$:v$[a, b, c]
$@+2+34$
$:for$for i in range(3):
    print(i $:v$+ 1 $:h$* $testDollarEnd$42)
    $testSubs$
    $if:macroifconst$
    print(a$:subscript$[1], $:kwd$end=2)
    a = $:gencomp$(x for x in range(3)), $:dict${a:1, b:2}
    a $:augassign$+= i $:inline if$if i $:is$is 0 else $:unary$-i
    $testDollar$
    $:if$if i $:compare$== 1:
        pass
    $:elif$elif i==2:
        pass
    $:else$else:
        pass
    $l1:
l2$pass
"""
print('original text:\n%s\n' % text)
segments = parseText(macroParser, text, 'nurdle.py')

if segments is not None:
    for segment in segments:
        pos, stmtList = segment
        print(repr(pos))
        for stmt in stmtList:
            for node in ast.walk(stmt):
                macroName = macroArgs = iconCreateFn = None
                if hasattr(node, 'macroName'):
                    print('annotated node %s with macro name %s' %
                        (node.__class__.__name__, node.macroName))
                if hasattr(node, 'macroArgs'):
                    print('annotated node %s with macro args %s' %
                          (node.__class__.__name__, node.macroArgs))
                if hasattr(node, 'iconCreationFunction'):
                    print('annotated node %s with icon creation function %s' %
                          (node.__class__.__name__, repr(node.iconCreationFunction)))
            astpretty.pprint(stmt)