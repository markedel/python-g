import ast, astpretty
import re
import tkinter

posPatternSrc = "\\$pos((\\+|\\-)\d*)((\\+|\\-)\\d*)\\$"
posMacroPattern = re.compile(posPatternSrc)
macroList = [(posPatternSrc, "pass", ast.Pass)]
annotatedAstTypes = set((ast.Pass,))
matchPattern = None

def addMacro(pattern, subs, astNode):
    """Add a macro to substitute text and add annotation data to extend the save-file and
    pasted-text format beyond the base Python syntax.  pattern is a regular expression
    used to match the macro, including the macro-introducing and terminating characters.
    subs is either a string containing fixed text to substitute, or a callable function
    for generating that text from the matched macro during processing.  astNode is used
    to help attach the matched content of the macro as annotation to the AST node (and
    eventually, icon) created by the macro.  astNode should be the AST node that will
    appear at the line number and column offset at which the macro substitution was done.
    If passed as None, no annotation will be attached."""
    global macroList, matchPattern, annotatedAstTypes
    individualPattern = re.compile(pattern)
    macroList.append((pattern, subs, astNode, individualPattern))
    if astNode is not None:
        annotatedAstTypes.add(astNode)
    matchPattern = None

def expandMacros(text):
    """Takes text in python_g clipboard/save-file text format, expands macros and returns
    three items:
        1) The macro-expanded text
        2) A dictionary for looking up AST nodes that the macros have requested to
           annotate.  The annotation dictionary is indexed by a tuple:
                (AST-class, line-number, column-offset).
        3) A list whose index is line numbers in the macro-expanded version of the text
           and whose content is the corresponding line number in the original text
           (before expansion)."""
    annotations = {}
    lineNumTranslate = []
    if matchPattern is None:
        _createMacroPattern()
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
            return None, {}, []
        if origChar == '\n':
            lineNumTranslate.append(origLineNum)
            origLineNum += 1
            modLineNum += 1
            modColNum = 0
            origLineStarts.append(origIdx+1)
            origIdx += 1
        elif origChar == '$':
            # Macro found.  Decide which one and get replacement text
            match = matchPattern.match(text, origIdx)
            if match is None:
                macroFailDialog(text, origIdx, origLineNum)
                return None, {}, []
            for i in range(len(macroList)):
                macroText = match.group('g%d'%i)
                if macroText is not None:
                    macroIdx = i
                    break
            else:
                macroFailDialog(text, origIdx, origLineNum)
                return None, {}, []
            pattern, subs, astNode, individualPattern = macroList[macroIdx]
            if callable(subs):
                replaceText = subs(macroText)
            else:
                replaceText = individualPattern.sub(subs, macroText)
            # Copy the text between the last macro and this one in to the output list
            textToCopy = text[modFragStart:origIdx]
            modTextFrags.append(textToCopy)
            # Copy the macro's replacement text in to the output list
            modTextFrags.append(replaceText)
            # If the macro wants to annotate an AST, add an entry to the annotations
            # array by AST class, line, and column (see ... for explanation of special
            # treatment of binary operators
            if astNode is not None:
                if astNode is ast.BinOp:
                    annotations[(astNode, *_binOpAdjLineCol(modLineNum, modColNum,
                        text, origIdx))] = macroText
                else:
                    annotations[(astNode, modLineNum, modColNum)] = macroText
            # Adjust line counts for newlines in macro or replaced text
            macroEndIdx = origIdx + len(macroText)
            origLineNum += text[origIdx:macroEndIdx].count('\n')
            modLines = replaceText.split('\n')
            for i in range(len(modLines) - 1):
                modLineNum += 1
                lineNumTranslate.append(origLineNum)
            if len(modLines) > 1:
                modColNum = len(modLines[-1])
            else:
                modColNum += len(macroText)
            origIdx += len(macroText)
            modFragStart = origIdx
        else:
            modColNum += 1
            origIdx += 1
    # Copy the text between the last macro and the end of the input text to the output
    modTextFrags.append(text[modFragStart:])
    # Consolidate the output fragments in to a single string, and return it and the
    # annotation dictionary and line number translation list
    return "".join(modTextFrags), annotations, lineNumTranslate

def _createMacroPattern():
    global matchPattern
    compositePattern = []
    for i, macro in enumerate(macroList):
        pattern = macro[0]
        groupName = "g%d" % i
        compositePattern.append("(?P<%s>%s)" % (groupName, pattern))
    print('pattern:', "|".join(compositePattern))
    matchPattern = re.compile("|".join(compositePattern))

def _binOpAdjLineCol(modLineNum, modColNum, text, origIdx):
    """BinOp ASTs, unfortunately, do not encode the line and column of the operator, but
     of the entire expression.  The code here, marches backward from the operator
     (actually the macro that will expand in to the operator) to find the first non-white
     character, and returns a line and column number matching that text position.  The
     annotation code for BinOps, likewise, does not use the line and column listed on
     the BinOp AST, but the line and column of the right side of its left argument."""
    for i in range(origIdx-1, -1, -1):
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
    return 0, 0

def parseText(text, fileName="Pasted Text"):
    """Parse save-file format (from clipboard or file) and return tuples pairing a window
    position with a list of AST nodes to form a sequence.  If the position is None,
    the segment should be attached to the window module sequence point."""
    # Expand macros
    expandedText, annotations, lineNumTranslate = expandMacros(text)
    if expandedText is None:
        return None
    print('expanded Text:\n%s' % expandedText)
    print('lineNumTranslate', lineNumTranslate)
    print('annotations', repr(annotations))
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
    # Add annotations to AST nodes
    notDone = set(annotations.keys())  # Temporary for testing
    for node in ast.walk(modAst):
        if node.__class__ in annotatedAstTypes:
            if node.__class__ is ast.BinOp:
                line = node.left.end_lineno
                col = node.left.end_col_offset
                key = (node.__class__, line, col)
            else:
                key = (node.__class__, node.lineno, node.col_offset)
            macro = annotations.get(key)
            if macro is not None:
                node.annotation = macro
                notDone.remove(key)
                print('annotated node %s with %s' % (node.__class__.__name__, macro))
    if len(notDone) != 0:
        print('Failed to find annotations:', notDone)
    # Split the parse results in to separately positioned segments
    currentSegment = []
    segments = [(None, currentSegment)]
    for node in modAst.body:
        if node.__class__ is ast.Pass:
            if hasattr(node, 'annotation') and node.annotation[:5] in ("$pos+", "$pos-"):
                currentSegment = []
                segments.append((_parsePosMacro(node.annotation), currentSegment))
        else:
            currentSegment.append(node)
    return segments

def _parsePosMacro(macroText):
    match = posMacroPattern.match(macroText)
    if match is None:
        print("Internal error in macro parsing")
        return 0, 0
    x = int(match.group(1))
    y = int(match.group(3))
    return x,y

def loadFile(fileName):
    with open(fileName, "r") as f:
        return parseText(f.read(), fileName)

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

addMacro("\\$\\[[hv]\\$", "[", ast.List)
addMacro("\\$\\+[hv]\\$", "+", ast.BinOp)
addMacro("\\$l1\\nl2\\$", "pass", ast.Pass)
text="""$pos-1+34$
$[v$a, b, c]
$pos+2+34$
for i in range(3):
    print(i $+v$ 1)
    $l1
l2$
x
"""
print('original text:\n%s\n' % text)
segments = parseText(text, 'nurdle.py')
if segments is not None:
    for segment in segments:
        pos, stmtList = segment
        print(repr(pos))
        for stmt in stmtList:
            astpretty.pprint(stmt)