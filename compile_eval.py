import ast, time
import numbers
import icon
import opicons
import blockicons
import nameicons
import listicons
import assignicons
import subscripticon

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
    return icons

def parseCodeBlock(bodyAst, window, location):
    x, y = location
    icons = []
    seqStartIcon = None
    for stmt in bodyAst:
        if isinstance(stmt, ast.Expr):
            stmtIcon = parseExpr(stmt.value, window)
            bodyIcons = None
        elif stmt.__class__ in (blockStmts):
            stmtIcon = parseStmt(stmt, window)
            bodyIcons = parseCodeBlock(stmt.body, window, location)
            stmtIcon.sites.seqOut.attach(stmtIcon, bodyIcons[0], 'seqIn')
            while stmt.__class__ is ast.If and len(stmt.orelse) == 1 and \
             stmt.orelse[0].__class__ is ast.If:
                # Process elif blocks.  The ast encodes these as a single if, nested
                # in and else (nested as many levels deep as there are elif clauses).
                elifIcon = blockicons.ElifIcon(window, location)
                condIcon = parseExpr(stmt.orelse[0].test, window)
                elifIcon.replaceChild(condIcon, 'condIcon')
                elifBlockIcons = parseCodeBlock(stmt.orelse[0].body, window, location)
                bodyIcons[-1].sites.seqOut.attach(bodyIcons[-1], elifIcon, 'seqIn')
                bodyIcons.append(elifIcon)
                elifIcon.sites.seqOut.attach(elifIcon, elifBlockIcons[0], 'seqIn')
                bodyIcons += elifBlockIcons
                stmtIcon.addElse(elifIcon)
                stmt = stmt.orelse[0]
            if stmt.__class__ in (ast.If, ast.For, ast.AsyncFor, ast.While) and \
             len(stmt.orelse) != 0:
                # Process else block (note that after elif processing above, stmt may in
                # some cases point to a nested statement being flattened out)
                elseIcon = blockicons.ElseIcon(window, location)
                elseBlockIcons = parseCodeBlock(stmt.orelse, window, location)
                bodyIcons[-1].sites.seqOut.attach(bodyIcons[-1], elseIcon, 'seqIn')
                bodyIcons.append(elseIcon)
                elseIcon.sites.seqOut.attach(elseIcon, elseBlockIcons[0], 'seqIn')
                bodyIcons += elseBlockIcons
                stmtIcon.addElse(elseIcon)
            blockEnd = stmtIcon.blockEnd
            bodyIcons[-1].sites.seqOut.attach(bodyIcons[-1], blockEnd, 'seqIn')
            bodyIcons.append(blockEnd)
        else:
            stmtIcon = parseStmt(stmt, window)
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

def parseStmt(stmt, window):
    if stmt.__class__ == ast.Assign:
        topIcon = assignicons.AssignIcon(len(stmt.targets), window)
        for i, tgt in enumerate(stmt.targets):
            if isinstance(tgt, ast.Tuple):
                tgtIcons = [parseExpr(t, window) for t in tgt.elts]
            else:
                tgtIcons = [parseExpr(tgt, window)]
            topIcon.insertChildren(tgtIcons, "targets%d" % i, 0)
        if isinstance(stmt.value, ast.Tuple):
            valueIcons = [parseExpr(v, window) for v in stmt.value.elts]
            topIcon.insertChildren(valueIcons, "values", 0)
        else:
            topIcon.replaceChild(parseExpr(stmt.value, window), "values_0")
        return topIcon
    if stmt.__class__ == ast.AugAssign:
        assignIcon = assignicons.AugmentedAssignIcon(binOps[stmt.op.__class__], window)
        targetIcon = parseExpr(stmt.target, window)
        assignIcon.replaceChild(targetIcon, "targetIcon")
        if isinstance(stmt.value, ast.Tuple):
            valueIcons = [parseExpr(v, window) for v in stmt.value.elts]
            assignIcon.insertChildren(valueIcons, "values", 0)
        else:
            assignIcon.replaceChild(parseExpr(stmt.value, window), "values_0")
        return assignIcon
    if stmt.__class__ == ast.While:
        topIcon = blockicons.WhileIcon(window=window)
        topIcon.replaceChild(parseExpr(stmt.test, window), 'condIcon')
        return topIcon
    if stmt.__class__ in (ast.For, ast.AsyncFor):
        isAsync = stmt.__class__ is ast.AsyncFor
        topIcon = blockicons.ForIcon(isAsync, window=window)
        if isinstance(stmt.target, ast.Tuple):
            tgtIcons = [parseExpr(t, window) for t in stmt.target.elts]
            topIcon.insertChildren(tgtIcons, "targets", 0)
        else:
            topIcon.replaceChild(parseExpr(stmt.target, window), "targets_0")
        if isinstance(stmt.iter, ast.Tuple):
            iterIcons = [parseExpr(i, window) for i in stmt.iter]
            topIcon.insertChildren(iterIcons, "iterIcons", 0)
        else:
            topIcon.replaceChild(parseExpr(stmt.iter, window), "iterIcons_0")
        return topIcon
    if stmt.__class__ == ast.If:
        topIcon = blockicons.IfIcon(window=window)
        topIcon.replaceChild(parseExpr(stmt.test, window), 'condIcon')
        return topIcon
    if stmt.__class__ in (ast.FunctionDef, ast.AsyncFunctionDef):
        isAsync = stmt.__class__ is ast.AsyncFunctionDef
        if hasattr(stmt.args, 'posonlyargs'):
            args = [arg.arg for arg in stmt.args.posonlyargs]
        else:
            args = []
        nPosOnly = len(args)
        defIcon = blockicons.DefIcon(isAsync, window=window)
        nameIcon = nameicons.IdentifierIcon(stmt.name, window)
        defIcon.replaceChild(nameIcon, 'nameIcon')
        defaults = [parseExpr(e, window) for e in stmt.args.defaults]
        if len(defaults) < len(stmt.args.args):
            # Weird rule in defaults list for ast that defaults can be shorter than args
            defaults = ([None] * (len(stmt.args.args) - len(defaults))) + defaults
        numArgs = 0
        for i, arg in enumerate(arg.arg for arg in stmt.args.args):
            default = defaults[i]
            argNameIcon = nameicons.IdentifierIcon(arg, window)
            if nPosOnly != 0 and numArgs == nPosOnly:
                posOnlyMarker = blockicons.PosOnlyMarkerIcon(window=window)
                defIcon.insertChild(posOnlyMarker, 'argIcons', numArgs)
                numArgs += 1
            if default is None:
                defIcon.insertChild(argNameIcon, 'argIcons', numArgs)
            else:
                defaultIcon = default
                argAssignIcon = listicons.ArgAssignIcon(window)
                argAssignIcon.replaceChild(argNameIcon, 'leftArg')
                argAssignIcon.replaceChild(defaultIcon, 'rightArg')
                defIcon.insertChild(argAssignIcon, "argIcons", numArgs)
            numArgs += 1
        varArg = stmt.args.vararg.arg if stmt.args.vararg is not None else None
        if varArg is not None:
            argNameIcon = nameicons.IdentifierIcon(varArg, window)
            starIcon = listicons.StarIcon(window)
            starIcon.replaceChild(argNameIcon, 'argIcon')
            defIcon.insertChild(starIcon, 'argIcons', numArgs)
            numArgs += 1
        kwOnlyArgs = [arg.arg for arg in stmt.args.kwonlyargs]
        kwDefaults = [parseExpr(e, window) for e in stmt.args.kw_defaults]
        if len(kwOnlyArgs) > 0 and varArg is None:
            defIcon.insertChild(listicons.StarIcon(window), 'argIcons', numArgs)
            numArgs += 1
        for i, arg in enumerate(kwOnlyArgs):
            argNameIcon = nameicons.IdentifierIcon(arg, window)
            if kwDefaults[i] is None:
                defIcon.insertChild(argNameIcon, 'argIcons', i)
            else:
                defaultIcon = kwDefaults[i]
                argAssignIcon = listicons.ArgAssignIcon(window)
                argAssignIcon.replaceChild(argNameIcon, 'leftArg')
                argAssignIcon.replaceChild(defaultIcon, 'rightArg')
                defIcon.insertChild(argAssignIcon, "argIcons", numArgs + i)
        numArgs += len(kwOnlyArgs)
        if stmt.args.kwarg is not None:
            argNameIcon = nameicons.IdentifierIcon(stmt.args.kwarg.arg, window)
            starStarIcon = listicons.StarStarIcon(window)
            starStarIcon.replaceChild(argNameIcon, 'argIcon')
            defIcon.insertChild(starStarIcon, 'argIcons', numArgs)
        return defIcon
    if stmt.__class__ is ast.ClassDef:
        hasArgs = len(stmt.bases) + len(stmt.keywords) > 0
        topIcon = blockicons.ClassDefIcon(hasArgs, window=window)
        nameIcon = nameicons.IdentifierIcon(stmt.name, window)
        topIcon.replaceChild(nameIcon, 'nameIcon')
        bases = [parseExpr(base, window) for base in stmt.bases]
        topIcon.insertChildren(bases, "argIcons", 0)
        kwdIcons = []
        for idx, kwd in enumerate(stmt.keywords):
            argAssignIcon = listicons.ArgAssignIcon(window)
            kwdIcon = nameicons.IdentifierIcon(kwd, window)
            valueIcon = parseExpr(kwd.value, window)
            argAssignIcon.replaceChild(kwdIcon, 'leftArg')
            argAssignIcon.replaceChild(valueIcon, 'rightArg')
            kwdIcons.append(argAssignIcon)
        topIcon.insertChildren(kwdIcons, "argIcons", len(bases))
        return topIcon
    if stmt.__class__ is ast.Return:
        topIcon = nameicons.ReturnIcon(window)
        if stmt.value is None:
            return topIcon
        if isinstance(stmt.value, ast.Tuple):
            valueIcons = [parseExpr(v, window) for v in stmt.value.elts]
            topIcon.insertChildren(valueIcons, "values", 0)
        else:
            topIcon.replaceChild(parseExpr(stmt.value, window), "values_0")
        return topIcon
    if stmt.__class__ in (ast.With, ast.AsyncWith):
        isAsync = isinstance(stmt, ast.AsyncWith)
        topIcon = blockicons.WithIcon(isAsync, window=window)
        for idx, item in enumerate(stmt.items):
            contextIcon = parseExpr(item.context_expr, window)
            if item.optional_vars is None:
                topIcon.insertChild(contextIcon, "values", idx)
            else:
                asIcon = blockicons.WithAsIcon(window)
                asIcon.replaceChild(contextIcon, "leftArg")
                asIcon.replaceChild(parseExpr(item.optional_vars, window), "rightArg")
                topIcon.insertChild(asIcon, "values", idx)
        return topIcon
    if stmt.__class__ is ast.Delete:
        topIcon = nameicons.DelIcon(window)
        targets = [parseExpr(t, window) for t in stmt.targets]
        topIcon.insertChildren(targets, "values", 0)
        return topIcon
    if stmt.__class__ is ast.Pass:
        return nameicons.PassIcon(window)
    if stmt.__class__ is ast.Continue:
        return nameicons.ContinueIcon(window)
    if stmt.__class__ is ast.Break:
        return nameicons.BreakIcon(window)
    if stmt.__class__ is ast.Global:
        topIcon = nameicons.GlobalIcon(window)
        nameIcons = [nameicons.IdentifierIcon(name, window) for name in stmt.names]
        topIcon.insertChildren(nameIcons, "values", 0)
        return topIcon
    if stmt.__class__ is ast.Nonlocal:
        topIcon = nameicons.NonlocalIcon(window)
        nameIcons = [nameicons.IdentifierIcon(name, window) for name in stmt.names]
        topIcon.insertChildren(nameIcons, "values", 0)
        return topIcon
    return (nameicons.IdentifierIcon, "**Couldn't Parse**")

def parseExpr(expr, window):
    if expr.__class__ == ast.UnaryOp:
        topIcon = opicons.UnaryOpIcon(unaryOps[expr.op.__class__], window)
        topIcon.replaceChild(parseExpr(expr.operand, window), "argIcon")
        return topIcon
    elif expr.__class__ == ast.BinOp:
        if expr.op.__class__ in (ast.Div, ast.FloorDiv):
            topIcon = opicons.DivideIcon(expr.op.__class__ is ast.FloorDiv, window)
            topIcon.replaceChild(parseExpr(expr.left, window), "topArg")
            topIcon.replaceChild(parseExpr(expr.right, window), "bottomArg")
            return topIcon
        topIcon = opicons.BinOpIcon(binOps[expr.op.__class__], window)
        topIcon.replaceChild(parseExpr(expr.left, window), "leftArg")
        topIcon.replaceChild(parseExpr(expr.right, window), "rightArg")
        return topIcon
    elif expr.__class__ == ast.BoolOp:
        topIcon = opicons.BinOpIcon(boolOps[expr.op.__class__], window)
        topIcon.replaceChild(parseExpr(expr.values[0], window), "leftArg")
        topIcon.replaceChild(parseExpr(expr.values[1], window), "rightArg")
        for value in expr.values[2:]:
            newTopIcon = opicons.BinOpIcon(boolOps[expr.op.__class__], window)
            newTopIcon.replaceChild(topIcon, "leftArg")
            newTopIcon.replaceChild(parseExpr(value, window), "rightArg")
            topIcon = newTopIcon
        return topIcon
    elif expr.__class__ == ast.Compare:
        # Note: this does not yet handle multi-comparison types
        topIcon = opicons.BinOpIcon(compareOps[expr.ops[0].__class__], window)
        topIcon.replaceChild(parseExpr(expr.left, window), "leftArg")
        topIcon.replaceChild(parseExpr(expr.comparators[0], window), "rightArg")
        return topIcon
    elif expr.__class__ == ast.Call:
        callIcon = listicons.CallIcon(window)
        argIcons = [parseExpr(e, window) for e in expr.args]
        for key in expr.keywords:
            valueIcon = parseExpr(key.value, window)
            if key.arg is None:
                starStarIcon = listicons.StarStarIcon(window)
                starStarIcon.replaceChild(valueIcon, 'argIcon')
                argIcons.append(starStarIcon)
            else:
                kwIcon = listicons.ArgAssignIcon(window)
                kwIcon.replaceChild(nameicons.IdentifierIcon(key.arg, window), 'leftArg')
                kwIcon.replaceChild(valueIcon, 'rightArg')
                argIcons.append(kwIcon)
        topIcon = parseExpr(expr.func, window)
        parentIcon = icon.findLastAttrIcon(topIcon)
        parentIcon.replaceChild(callIcon, "attrIcon")
        callIcon.insertChildren(argIcons, "argIcons", 0)
        return topIcon
    elif expr.__class__ == ast.Num:
        return nameicons.NumericIcon(expr.n, window)
    elif expr.__class__ == ast.Str:
        return (nameicons.StringIcon, expr.s)
    elif expr.__class__ == ast.Constant:
        if isinstance(expr.value, numbers.Number) or expr.value is None:
            # Note that numbers.Number includes True and False
            return nameicons.NumericIcon(expr.value, window)
        elif isinstance(expr.value, str) or isinstance(expr.value, bytes):
            return nameicons.StringIcon(expr.value, window)
        if isinstance(expr.value, type(...)):
            return nameicons.NumericIcon(expr.value, window)
        # Documentation threatens to return constant tuples and frozensets (which could
        # get quite complex), but 3.8 seems to stick to strings and numbers
        return nameicons.IdentifierIcon("**Couldn't Parse Constant**", window)
    # FormattedValue, JoinedStr, Bytes, List, Tuple, Set, Dict, Ellipsis, NamedConstant
    elif expr.__class__ == ast.Name:
        return nameicons.IdentifierIcon(expr.id, window)
    elif expr.__class__ == ast.Starred:
        topIcon = listicons.StarIcon(window)
        topIcon.replaceChild(parseExpr(expr.value, window), "argIcon")
        return topIcon
    elif expr.__class__ == ast.NameConstant:
        return nameicons.NumericIcon(expr.value, window)
    elif expr.__class__ == ast.List:
        topIcon = listicons.ListIcon(window)
        childIcons = [parseExpr(e, window) for e in expr.elts]
        topIcon.insertChildren(childIcons, "argIcons", 0)
        return topIcon
    elif expr.__class__ == ast.Tuple:
        topIcon = listicons.TupleIcon(window)
        childIcons = [parseExpr(e, window) for e in expr.elts]
        topIcon.insertChildren(childIcons, "argIcons", 0)
        return topIcon
    elif expr.__class__ == ast.Dict:
        topIcon = listicons.DictIcon(window)
        argIcons = []
        for i, key in enumerate(expr.keys):
            value = parseExpr(expr.values[i], window)
            if key is None:
                starStar = listicons.StarStarIcon(window)
                starStar.replaceChild(value, "argIcon")
                argIcons.append(starStar)
            else:
                dictElem = listicons.DictElemIcon(window)
                dictElem.replaceChild(parseExpr(key, window), "leftArg")
                dictElem.replaceChild(value, "rightArg")
                argIcons.append(dictElem)
        topIcon.insertChildren(argIcons, "argIcons", 0)
        return topIcon
    elif expr.__class__ == ast.Attribute:
        # Note that the icon hierarchy and the AST hierarchy differ with respect to
        # attributes. ASTs put the attribute at the top, we put the root icon at the top.
        attrIcon = nameicons.AttrIcon(expr.attr, window)
        topIcon = parseExpr(expr.value, window)
        parentIcon = icon.findLastAttrIcon(topIcon)
        parentIcon.replaceChild(attrIcon, "attrIcon")
        return topIcon
    elif expr.__class__ is ast.Yield:
        topIcon = nameicons.YieldIcon(window)
        if expr.value is None:
            return topIcon
        if isinstance(expr.value, ast.Tuple):
            valueIcons = [parseExpr(v, window) for v in expr.value.elts]
            topIcon.insertChildren(valueIcons, "values", 0)
        else:
            topIcon.replaceChild(parseExpr(expr.value, window), "values_0")
        return topIcon
    elif expr.__class__ is ast.YieldFrom:
        topIcon = nameicons.YieldFromIcon(window)
        topIcon.replaceChild(parseExpr(expr.value, window), "argIcon")
        return topIcon
    elif expr.__class__ is ast.Await:
        topIcon = nameicons.AwaitIcon(window)
        topIcon.replaceChild(parseExpr(expr.value, window), "argIcon")
        return topIcon
    elif expr.__class__ == ast.Subscript:
        if expr.slice.__class__ == ast.Index:
            slice = [expr.slice.value]
        elif expr.slice.__class__ == ast.Slice:
            slice = [expr.slice.lower, expr.slice.upper, expr.slice.step]
        elif expr.slice.__class__ == ast.ExtSlice:
            return nameicons.TextIcon("**Extended slices not supported***")
        else:
            return nameicons.TextIcon("**Unexpected slice type not supported***")
        nSlices = len(slice)
        subscriptIcon = subscripticon.SubscriptIcon(nSlices, window)
        if slice[0] is not None:
            subscriptIcon.replaceChild(parseExpr(slice[0], window), "indexIcon")
        if nSlices >= 2 and slice[1] is not None:
            subscriptIcon.replaceChild(parseExpr(slice[1], window), "upperIcon")
        if nSlices >= 3 and slice[2] is not None:
            subscriptIcon.replaceChild(parseExpr(slice[2], window), "stepIcon")
        topIcon = parseExpr(expr.value, window)
        parentIcon = icon.findLastAttrIcon(topIcon)
        parentIcon.replaceChild(subscriptIcon, "attrIcon")
        return topIcon
    elif expr.__class__ in (ast.ListComp, ast.SetComp, ast.GeneratorExp, ast.DictComp):
        if expr.__class__ is ast.DictComp:
            tgt = expr.value
            key = expr.key
        else:
            tgt = expr.elt
            key = None
        return makeComprehension(window, expr.__class__, tgt, key, expr.generators)
    elif expr.__class__ is ast.Set:
        topIcon = listicons.DictIcon(window)
        childIcons = [parseExpr(e, window) for e in expr.elts]
        topIcon.insertChildren(childIcons, "argIcons", 0)
        return topIcon
    else:
        return (nameicons.IdentifierIcon, "**Couldn't Parse**")

def makeComprehension(window, astType, tgt, key, generators):
    cprhType = {ast.ListComp: listicons.ListIcon, ast.SetComp: listicons.DictIcon,
        ast.GeneratorExp: listicons.TupleIcon, ast.DictComp: listicons.DictIcon}[astType]
    topIcon = cprhType(window=window)
    if key is None:
        topIcon.replaceChild(parseExpr(tgt, window), 'argIcons_0')
    else:
        dictElem = listicons.DictElemIcon(window)
        dictElem.replaceChild(parseExpr(key, window), "leftArg")
        dictElem.replaceChild(parseExpr(tgt, window), "rightArg")
        topIcon.replaceChild(dictElem, 'argIcons_0')
    clauseIdx = 0
    for gen in generators:
        forIcon = listicons.CprhForIcon(gen.is_async, window)
        if isinstance(gen.target, ast.Tuple):
            tgtIcons = [parseExpr(t, window) for t in gen.target.elts]
            forIcon.insertChildren(tgtIcons, "targets", 0)
        else:
            forIcon.insertChild(parseExpr(gen.target, window), "targets", 0)
        forIcon.replaceChild(parseExpr(gen.iter, window), 'iterIcon')
        topIcon.insertChild(forIcon, "cprhIcons", clauseIdx)
        clauseIdx += 1
        for i in gen.ifs:
            ifIcon = listicons.CprhIfIcon(window)
            testIcon = parseExpr(i, window)
            ifIcon.replaceChild(testIcon, 'testIcon')
            topIcon.insertChild(ifIcon, "cprhIcons", clauseIdx)
            clauseIdx += 1
    return topIcon
