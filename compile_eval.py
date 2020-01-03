import ast, astpretty
import icon

binOps = {ast.Add:'+', ast.Sub:'-', ast.Mult:'*', ast.Div:'/', ast.FloorDiv:'//', ast.Mod:'%', ast.Pow:'**',
        ast.LShift:'<<', ast.RShift:'>>', ast.BitOr:'|', ast.BitXor:'^', ast.BitAnd:'&', ast.MatMult:'@'}

unaryOps = {ast.UAdd:'+', ast.USub:'-', ast.Not:'not', ast.Invert:'~'}

boolOps = {ast.And:'and', ast.Or:'or'}

compareOps = {ast.Eq:'==', ast.NotEq:'!=', ast.Lt:'<', ast.LtE:'<=', ast.Gt:'>', ast.GtE:'>=', ast.Is:'is',
        ast.IsNot:'is not', ast.In:'in', ast.NotIn:'not in'}

def parsePasted(text, window, location):
    try:
        modAst = ast.parse(text, "Pasted text")
    except:
        return None
    if not isinstance(modAst, ast.Module):
        return None
    exprList = [expr.value for expr in modAst.body if isinstance(expr, ast.Expr)]
    if len(exprList) == 0:
        return None
    x, y = location
    icons = []
    for expr in exprList:
        topIcon = makeIcons(parseExpr(expr), window, x, y)
        topIcon.layout((x, y))
        icons.append(topIcon)
        y += 30 # Figure out how to space multiple expressions, later
    return icons

def parseExprToAst(text):
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

def parseExpr(expr):
    fn = 'functionIcon'
    id = 'identifierIcon'
    val = 'numericIcon'
    st = 'stringIcon'
    bin = 'binOpIcon'
    unary = 'unaryOpIcon'
    div = 'divideIcon'
    lis = 'listIcon'
    tup = 'tupleIcon'
    if expr.__class__ == ast.UnaryOp:
        return (unary, unaryOps[expr.op.__class__], parseExpr(expr.operand))
    elif expr.__class__ == ast.BinOp:
        if expr.op.__class__ is ast.Div:
            return (div, False, parseExpr(expr.left), parseExpr(expr.right))
        elif expr.op.__class__ is ast.FloorDiv:
            return (div, True, parseExpr(expr.left), parseExpr(expr.right))
        return (bin, binOps[expr.op.__class__], parseExpr(expr.left), parseExpr(expr.right))
    elif expr.__class__ == ast.BoolOp:
        return (bin, boolOps[expr.op.__class__], *(parseExpr(e) for e in expr.values))
    elif expr.__class__ == ast.Compare:
        # Note: this does not handle multi-comparison types
        return (fn, compareOps[expr.ops[0].__class__], parseExpr(expr.left), parseExpr(expr.comparators[0]))
    elif expr.__class__ == ast.Call:
        # No keywords or other cool stuff, yet
        return (fn, expr.func.id, *(parseExpr(e) for e in expr.args))
    elif expr.__class__ == ast.Num:
        return (val, expr.n)
    elif expr.__class__ == ast.Str:
        return (st, expr.s)
    # FormattedValue, JoinedStr, Bytes, List, Tuple, Set, Dict, Ellipsis, NamedConstant
    elif expr.__class__ == ast.Name:
        return (id, expr.id)
    elif expr.__class__ == ast.NameConstant:
        return (val, expr.value)  # True and False as number is a bit weird
    elif expr.__class__ == ast.List:
        return (lis, *(parseExpr(e) for e in expr.elts))
    elif expr.__class__ == ast.Tuple:
        return (tup, *(parseExpr(e) for e in expr.elts))
    else:
        return (id, "**Couldn't Parse**")

def makeIcons(parsedExpr, window, x, y):
    if parsedExpr[0] == 'identifierIcon':
        return icon.IdentifierIcon(parsedExpr[1], window, (x, y))
    if parsedExpr[0] == 'numericIcon':
        return icon.NumericIcon(parsedExpr[1], window, (x, y))
    if parsedExpr[0] == 'stringIcon':
        return icon.StringIcon(parsedExpr[1], window, (x, y))
    if parsedExpr[0] == 'functionIcon':
        topIcon = icon.FnIcon(parsedExpr[1], window, (x, y))
        childIcons = [makeIcons(pe, window, x, y) for pe in parsedExpr[2:]]
        topIcon.insertChildren(childIcons, "argIcons", 0)
        return topIcon
    if parsedExpr[0] == 'unaryOpIcon':
        topIcon = icon.UnaryOpIcon(parsedExpr[1], window, (x, y))
        topIcon.replaceChild(makeIcons(parsedExpr[2], window, x, y), "argIcon")
        return topIcon
    if parsedExpr[0] == 'binOpIcon':
        topIcon = icon.BinOpIcon(parsedExpr[1], window, (x, y))
        topIcon.replaceChild(makeIcons(parsedExpr[2], window, x, y), "leftArg")
        topIcon.replaceChild(makeIcons(parsedExpr[3], window, x, y), "rightArg")
        return topIcon
    if parsedExpr[0] == 'divideIcon':
        topIcon = icon.DivideIcon(window, (x, y), floorDiv=parsedExpr[1])
        topIcon.replaceChild(makeIcons(parsedExpr[2], window, x, y), "topArg")
        topIcon.replaceChild(makeIcons(parsedExpr[3], window, x, y), "bottomArg")
        return topIcon
    if parsedExpr[0] == 'listIcon':
        topIcon = icon.ListIcon(window, (x, y))
        childIcons = [makeIcons(pe, window, x, y) for pe in parsedExpr[1:]]
        topIcon.insertChildren(childIcons, "argIcons", 0)
        return topIcon
    if parsedExpr[0] == 'tupleIcon':
        topIcon = icon.TupleIcon(window, (x, y))
        childIcons = [makeIcons(pe, window, x, y) for pe in parsedExpr[1:]]
        topIcon.insertChildren(childIcons, "argIcons", 0)
        return topIcon
    else:
        return icon.TextIcon("**Internal Parse Error**", window, (x,y))
