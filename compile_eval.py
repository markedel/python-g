import ast, astpretty
import icon

binOps = {ast.Add:'+', ast.Sub:'-', ast.Mult:'*', ast.Div:'/', ast.FloorDiv:'//',
 ast.Mod:'%', ast.Pow:'**', ast.LShift:'<<', ast.RShift:'>>', ast.BitOr:'|',
 ast.BitXor:'^', ast.BitAnd:'&', ast.MatMult:'@'}

unaryOps = {ast.UAdd:'+', ast.USub:'-', ast.Not:'not', ast.Invert:'~'}

boolOps = {ast.And:'and', ast.Or:'or'}

compareOps = {ast.Eq:'==', ast.NotEq:'!=', ast.Lt:'<', ast.LtE:'<=', ast.Gt:'>',
 ast.GtE:'>=', ast.Is:'is', ast.IsNot:'is not', ast.In:'in', ast.NotIn:'not in'}

blockStmts = {ast.If, ast.While, ast.For, ast.Try, ast.ExceptHandler, ast.With,
 ast.FunctionDef, ast.ClassDef, ast.AsyncFor, ast.AsyncWith, ast.AsyncFunctionDef}

def parsePasted(text, window, location):
    try:
        modAst = ast.parse(text, "Pasted text")
    except:
        return None
    if not isinstance(modAst, ast.Module):
        return None
    if len(modAst.body) == 0:
        return None
    icons = parseCodeBlock(modAst.body, window, location)
    if len(icons) == 0:
        return None
    window.layoutIconsInSeq(icons[0])
    return icons

def parseCodeBlock(bodyAst, window, location):
    x, y = location
    icons = []
    seqStartIcon = None
    for stmt in bodyAst:
        if isinstance(stmt, ast.Expr):
            stmtIcon = makeIcons(parseExpr(stmt.value), window, x, y)
            bodyIcons = None
        elif stmt.__class__ in (blockStmts):
            stmtIcon = makeIcons(parseStmt(stmt), window, x, y)
            bodyIcons = parseCodeBlock(stmt.body, window, location)
            if bodyIcons is not None:
                blockEnd = stmtIcon.blockEnd
                stmtIcon.sites.seqOut.attach(stmtIcon, bodyIcons[0], 'seqIn')
                bodyIcons[-1].sites.seqOut.attach(bodyIcons[-1], blockEnd, 'seqIn')
                bodyIcons.append(blockEnd)
        else:
            stmtIcon = makeIcons(parseStmt(stmt), window, x, y)
            bodyIcons = None
        if seqStartIcon is None:
            seqStartIcon = stmtIcon
        elif icons[-1].hasSite('seqOut') and stmtIcon.hasSite('seqIn'):
            # Link the statement to the previous statement
            icons[-1].sites.seqOut.attach(icons[-1], stmtIcon, 'seqIn')
        else:
            print('Cannot link icons (no sequence sites)') # Shouldn't happen
        icons.append(stmtIcon)
        if bodyIcons is not None:
            icons += bodyIcons
    return icons

def parseExprToAst(text):  #... Not used. what is this for?
    try:
        modAst = ast.parse(text, "Pasted text")
    except:
        return None
    if not isinstance(modAst, ast.Module):
        return None
    if len(modAst.body) != 1:
        return None
    if not isinstance(modAst.body[0], ast.Expr):
        return None
    return modAst.body[0].value

def parseStmt(stmt):
    if stmt.__class__ == ast.Assign:
        targets = [parseExpr(e) for e in stmt.targets]
        return (icon.AssignIcon, targets,  parseExpr(stmt.value))
    if stmt.__class__ == ast.While:
        return (icon.WhileIcon, parseExpr(stmt.test))
    return (icon.IdentifierIcon, "**Couldn't Parse**")

def parseExpr(expr):
    if expr.__class__ == ast.UnaryOp:
        return (icon.UnaryOpIcon, unaryOps[expr.op.__class__], parseExpr(expr.operand))
    elif expr.__class__ == ast.BinOp:
        if expr.op.__class__ is ast.Div:
            return (icon.DivideIcon, False, parseExpr(expr.left), parseExpr(expr.right))
        elif expr.op.__class__ is ast.FloorDiv:
            return (icon.DivideIcon, True, parseExpr(expr.left), parseExpr(expr.right))
        return (icon.BinOpIcon, binOps[expr.op.__class__], parseExpr(expr.left),
         parseExpr(expr.right))
    elif expr.__class__ == ast.BoolOp:
        return (icon.BinOpIcon, boolOps[expr.op.__class__],
         *(parseExpr(e) for e in expr.values))
    elif expr.__class__ == ast.Compare:
        # Note: this does not handle multi-comparison types
        return (icon.BinOpIcon, compareOps[expr.ops[0].__class__], parseExpr(expr.left),
         parseExpr(expr.comparators[0]))
    elif expr.__class__ == ast.Call:
        # No keywords or other cool stuff, yet
        return (icon.FnIcon, expr.func.id, *(parseExpr(e) for e in expr.args))
    elif expr.__class__ == ast.Num:
        return (icon.NumericIcon, expr.n)
    elif expr.__class__ == ast.Str:
        return (icon.StringIcon, expr.s)
    # FormattedValue, JoinedStr, Bytes, List, Tuple, Set, Dict, Ellipsis, NamedConstant
    elif expr.__class__ == ast.Name:
        return (icon.IdentifierIcon, expr.id)
    elif expr.__class__ == ast.NameConstant:
        return (icon.NumericIcon, expr.value)  # True and False as number is a bit weird
    elif expr.__class__ == ast.List:
        return (icon.ListIcon, *(parseExpr(e) for e in expr.elts))
    elif expr.__class__ == ast.Tuple:
        return (icon.TupleIcon, *(parseExpr(e) for e in expr.elts))
    elif expr.__class__ == ast.Attribute:
        return (icon.AttrIcon, expr.attr, parseExpr(expr.value))
    elif expr.__class__ == ast.Subscript:
        if expr.slice.__class__ == ast.Index:
            slice = [expr.slice.value]
        elif expr.slice.__class__ == ast.Slice:
            slice = [expr.slice.lower, expr.slice.upper, expr.slice.step]
        parsedSlice = [None if e is None else parseExpr(e) for e in slice]
        if len(slice) == 3 and parsedSlice[2] is None:
            parsedSlice = parsedSlice[:2]
        return (icon.SubscriptIcon, parsedSlice, parseExpr(expr.value))
    else:
        return (icon.IdentifierIcon, "**Couldn't Parse**")

def makeIcons(parsedExpr, window, x, y):
    iconClass = parsedExpr[0]
    if iconClass in (icon.IdentifierIcon, icon.NumericIcon, icon.StringIcon):
        return iconClass(parsedExpr[1], window, (x, y))
    if iconClass is icon.FnIcon:
        topIcon = iconClass(parsedExpr[1], window, (x, y))
        childIcons = [makeIcons(pe, window, x, y) for pe in parsedExpr[2:]]
        topIcon.insertChildren(childIcons, "argIcons", 0)
        return topIcon
    if iconClass is icon.UnaryOpIcon:
        topIcon = iconClass(parsedExpr[1], window, (x, y))
        topIcon.replaceChild(makeIcons(parsedExpr[2], window, x, y), "argIcon")
        return topIcon
    if iconClass is icon.BinOpIcon:
        topIcon = iconClass(parsedExpr[1], window, (x, y))
        topIcon.replaceChild(makeIcons(parsedExpr[2], window, x, y), "leftArg")
        topIcon.replaceChild(makeIcons(parsedExpr[3], window, x, y), "rightArg")
        return topIcon
    if iconClass is icon.DivideIcon:
        topIcon = iconClass(parsedExpr[1], window, (x, y))
        topIcon.replaceChild(makeIcons(parsedExpr[2], window, x, y), "topArg")
        topIcon.replaceChild(makeIcons(parsedExpr[3], window, x, y), "bottomArg")
        return topIcon
    if iconClass in (icon.ListIcon, icon.TupleIcon):
        topIcon = iconClass(window, location=(x, y))
        childIcons = [makeIcons(pe, window, x, y) for pe in parsedExpr[1:]]
        topIcon.insertChildren(childIcons, "argIcons", 0)
        return topIcon
    if iconClass is icon.AssignIcon:
        tgts = parsedExpr[1]
        topIcon = iconClass(len(tgts), window, (x, y))
        for i, tgt in enumerate(tgts):
            if tgt[0] is icon.TupleIcon:
                tgtIcons = [makeIcons(t, window, x, y) for t in tgt[1:]]
            else:
                tgtIcons = [makeIcons(tgt, window, x, y)]
            topIcon.insertChildren(tgtIcons, "targets%d" % i, 0)
        if parsedExpr[2][0] is icon.TupleIcon:
            valueIcons = [makeIcons(v, window, x, y) for v in parsedExpr[2][1:]]
            topIcon.insertChildren(valueIcons, "values", 0)
        else:
            topIcon.replaceChild(makeIcons(parsedExpr[2], window, x, y), "values_0")
        return topIcon
    if iconClass is icon.AttrIcon:
        attrIcon = iconClass(parsedExpr[1], window)
        topIcon = makeIcons(parsedExpr[2], window, x, y)
        parentIcon = icon.findLastAttrIcon(topIcon)
        parentIcon.replaceChild(attrIcon, "attrIcon")
        return topIcon
    if iconClass is icon.SubscriptIcon:
        nSlices = len(parsedExpr[1])
        subscriptIcon = iconClass(nSlices, window, (x, y))
        subscriptIcon.replaceChild(makeIcons(parsedExpr[1][0], window, x, y), "indexIcon")
        if nSlices >= 2 and parsedExpr[1][1] is not None:
            subscriptIcon.replaceChild(makeIcons(parsedExpr[1][1], window, x, y),
                "upperIcon")
        if nSlices >= 3 and parsedExpr[1][2] is not None:
            subscriptIcon.replaceChild(makeIcons(parsedExpr[1][2], window, x, y),
                "stepIcon")
        topIcon = makeIcons(parsedExpr[2], window, x, y)
        parentIcon = icon.findLastAttrIcon(topIcon)
        parentIcon.replaceChild(subscriptIcon, "attrIcon")
        return topIcon
    if iconClass is icon.WhileIcon:
        topIcon = iconClass(window, (x, y))
        topIcon.replaceChild(makeIcons(parsedExpr[1], window, x, y), 'condIcon')
        return topIcon
    return icon.TextIcon("**Internal Parse Error**", window, (x,y))
