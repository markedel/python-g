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
        topIcon.layout(location)
        icons.append(topIcon)
        y += 10 # Figure out how to space multiple expressions, later
    return icons

def parseExpr(expr):
    fn = 'functionIcon'
    id = 'identIcon'
    bin = 'binOpIcon'
    div = 'divideIcon'
    if expr.__class__ == ast.UnaryOp:
        return (fn, unaryOps[expr.op.__class__], parseExpr(expr.operand))
    elif expr.__class__ == ast.BinOp:
        if expr.op.__class__ is ast.Div:
            return (div, parseExpr(expr.left), parseExpr(expr.right))
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
        return (id, str(expr.n))
    elif expr.__class__ == ast.Str:
        return (id, '"' + expr.s + '"')
    # FormattedValue, JoinedStr, Bytes, List, Tuple, Set, Dict, Ellipsis, NamedConstant
    elif expr.__class__ == ast.Name:
        return (id, expr.id)
    else:
        return (id, "**Couldn't Parse**")

def makeIcons(parsedExpr, window, x, y):
    if parsedExpr[0] == 'identIcon':
        return icon.IdentIcon(parsedExpr[1], window, (x, y))
    if parsedExpr[0] == 'functionIcon':
        topIcon = icon.FnIcon(parsedExpr[1], window, (x, y))
        childIcons = [makeIcons(pe, window, x, y) for pe in parsedExpr[2:]]
        topIcon.insertChildren(childIcons, ("insertInput", 0))
        return topIcon
    if parsedExpr[0] == 'binOpIcon':
        topIcon = icon.BinOpIcon(parsedExpr[1], window, (x, y))
        topIcon.replaceChild(makeIcons(parsedExpr[2], window, x, y), ("input", 0))
        topIcon.replaceChild(makeIcons(parsedExpr[3], window, x, y), ("input", 1))
        return topIcon
    if parsedExpr[0] == 'divideIcon':
        topIcon = icon.DivideIcon(window, (x, y))
        topIcon.replaceChild(makeIcons(parsedExpr[1], window, x, y), ("input", 0))
        topIcon.replaceChild(makeIcons(parsedExpr[2], window, x, y), ("input", 1))
        return topIcon
    else:
        return icon.IdentIcon("**Internal Parse Error**", window, (x,y))
