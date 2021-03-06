import ast, time
import numbers
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
            stmtIcon.sites.seqOut.attach(stmtIcon, bodyIcons[0], 'seqIn')
            while stmt.__class__ is ast.If and len(stmt.orelse) == 1 and \
             stmt.orelse[0].__class__ is ast.If:
                # Process elif blocks.  The ast encodes these as a single if, nested
                # in and else (nested as many levels deep as there are elif clauses).
                elifIcon = icon.ElifIcon(window, location)
                condIcon = makeIcons(parseExpr(stmt.orelse[0].test), window, x, y)
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
                elseIcon = icon.ElseIcon(window, location)
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
    if stmt.__class__ == ast.AugAssign:
        target = parseExpr(stmt.target)
        op = binOps[stmt.op.__class__]
        value = parseExpr(stmt.value)
        return (icon.AugmentedAssignIcon, target, op, value)
    if stmt.__class__ == ast.While:
        return (icon.WhileIcon, parseExpr(stmt.test))
    if stmt.__class__ in (ast.For, ast.AsyncFor):
        isAsync = stmt.__class__ is ast.AsyncFor
        return (icon.ForIcon, isAsync, parseExpr(stmt.target), parseExpr(stmt.iter))
    if stmt.__class__ == ast.If:
        return (icon.IfIcon, parseExpr(stmt.test))
    if stmt.__class__ in (ast.FunctionDef, ast.AsyncFunctionDef):
        isAsync = stmt.__class__ is ast.AsyncFunctionDef
        if hasattr(stmt.args, 'posonlyargs'):
            args = [arg.arg for arg in stmt.args.posonlyargs]
        else:
            args = []
        nPosOnly = len(args)
        args += [arg.arg for arg in stmt.args.args]
        defaults = [parseExpr(e) for e in stmt.args.defaults]
        varArg = stmt.args.vararg.arg if stmt.args.vararg is not None else None
        kwOnlyArgs = [arg.arg for arg in stmt.args.kwonlyargs]
        kwDefaults = [parseExpr(e) for e in stmt.args.kw_defaults]
        kwArg = stmt.args.kwarg.arg if stmt.args.kwarg is not None else None
        return (icon.DefIcon, isAsync, stmt.name, args, nPosOnly, defaults, varArg,
         kwOnlyArgs, kwDefaults, kwArg)
    if stmt.__class__ is ast.ClassDef:
        bases = [parseExpr(base) for base in stmt.bases]
        keywords = [(kwd.arg, parseExpr(kwd.value)) for kwd in stmt.keywords]
        return (icon.ClassDefIcon, stmt.name, bases, keywords)
    if stmt.__class__ is ast.Return:
        return (icon.ReturnIcon, None if stmt.value is None else parseExpr(stmt.value))
    if stmt.__class__ in (ast.With, ast.AsyncWith):
        withItems = []
        for item in stmt.items:
            contextExpr = parseExpr(item.context_expr)
            optVars = None if item.optional_vars is None else parseExpr(item.optional_vars)
            withItems.append((contextExpr, optVars))
        isAsync = isinstance(stmt, ast.AsyncWith)
        return (icon.WithIcon, isAsync, withItems)
    if stmt.__class__ is ast.Delete:
        return (icon.DelIcon, [parseExpr(e) for e in stmt.targets])
    if stmt.__class__ is ast.Pass:
        return (icon.PassIcon,)
    if stmt.__class__ is ast.Continue:
        return (icon.ContinueIcon,)
    if stmt.__class__ is ast.Break:
        return (icon.BreakIcon,)
    if stmt.__class__ is ast.Global:
        return (icon.GlobalIcon, stmt.names)
    if stmt.__class__ is ast.Nonlocal:
        return (icon.NonlocalIcon, stmt.names)
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
        args = [parseExpr(e) for e in expr.args]
        keywords = {k.arg:parseExpr(k.value) for k in expr.keywords}
        return (icon.CallIcon, parseExpr(expr.func), args, keywords)
    elif expr.__class__ == ast.Num:
        return (icon.NumericIcon, expr.n)
    elif expr.__class__ == ast.Str:
        return (icon.StringIcon, expr.s)
    elif expr.__class__ == ast.Constant:
        if isinstance(expr.value, numbers.Number) or expr.value is None:
            return (icon.NumericIcon, expr.value)  # Numbers includes True and False
        if isinstance(expr.value, str) or isinstance(expr.value, bytes):
            return (icon.StringIcon, expr.value)
        # Documentation threatens to return constant tuples and frozensets (which could
        # get quite complex), but 3.8 seems to stick to strings and numbers
        return (icon.IdentifierIcon, "**Couldn't Parse Non number/string const**")
    # FormattedValue, JoinedStr, Bytes, List, Tuple, Set, Dict, Ellipsis, NamedConstant
    elif expr.__class__ == ast.Name:
        return (icon.IdentifierIcon, expr.id)
    elif expr.__class__ == ast.Starred:
        return (icon.StarIcon, parseExpr(expr.value))
    elif expr.__class__ == ast.NameConstant:
        return (icon.NumericIcon, expr.value)  # True and False as number is a bit weird
    elif expr.__class__ == ast.List:
        return (icon.ListIcon, *(parseExpr(e) for e in expr.elts))
    elif expr.__class__ == ast.Tuple:
        return (icon.TupleIcon, *(parseExpr(e) for e in expr.elts))
    elif expr.__class__ == ast.Dict:
        keys = [None if e is None else parseExpr(e) for e in expr.keys]
        values = [parseExpr(e) for e in expr.values]
        return (icon.DictIcon, keys, values)
    elif expr.__class__ == ast.Attribute:
        return (icon.AttrIcon, expr.attr, parseExpr(expr.value))
    elif expr.__class__ is ast.Yield:
        return (icon.YieldIcon, None if expr.value is None else parseExpr(expr.value))
    elif expr.__class__ is ast.YieldFrom:
        return (icon.YieldFromIcon, parseExpr(expr.value))
    elif expr.__class__ is ast.Await:
        return (icon.AwaitIcon, parseExpr(expr.value))
    elif expr.__class__ == ast.Subscript:
        if expr.slice.__class__ == ast.Index:
            slice = [expr.slice.value]
        elif expr.slice.__class__ == ast.Slice:
            slice = [expr.slice.lower, expr.slice.upper, expr.slice.step]
        parsedSlice = [None if e is None else parseExpr(e) for e in slice]
        if len(slice) == 3 and parsedSlice[2] is None:
            parsedSlice = parsedSlice[:2]
        return (icon.SubscriptIcon, parsedSlice, parseExpr(expr.value))
    elif expr.__class__ in (ast.ListComp, ast.SetComp, ast.GeneratorExp, ast.DictComp):
        compType = {ast.ListComp:icon.ListIcon, ast.SetComp:icon.DictIcon,
         ast.GeneratorExp:icon.TupleIcon, ast.DictComp:icon.DictIcon}[expr.__class__]
        if expr.__class__ is ast.DictComp:
            tgt = parseExpr(expr.value)
            key = parseExpr(expr.key)
        else:
            tgt = parseExpr(expr.elt)
            key = None
        generators = []
        for gen in expr.generators:
            genTarget = parseExpr(gen.target)
            genIter = parseExpr(gen.iter)
            genIfs = [parseExpr(i) for i in gen.ifs]
            generators.append((genTarget, genIter, genIfs, gen.is_async))
        return ("comprehension", compType, tgt, key, generators)
    elif expr.__class__ is ast.Set:
        return ("set", [parseExpr(e) for e in expr.elts])
    else:
        return (icon.IdentifierIcon, "**Couldn't Parse**")

def makeIcons(parsedExpr, window, x, y):
    iconClass = parsedExpr[0]
    if iconClass in (icon.PassIcon, icon.ContinueIcon, icon.BreakIcon):
        return iconClass(window, (x, y))
    if iconClass in (icon.IdentifierIcon, icon.NumericIcon, icon.StringIcon):
        return iconClass(parsedExpr[1], window, (x, y))
    if iconClass is icon.CallIcon:
        func, args, keywords = parsedExpr[1:]
        callIcon = iconClass(window, (x, y))
        argIcons = [makeIcons(pe, window, x, y) for pe in args]
        for key, val in keywords.items():
            valueIcon = makeIcons(val, window, x, y)
            if key is None:
                starStarIcon = icon.StarStarIcon(window)
                starStarIcon.replaceChild(valueIcon, 'argIcon')
                argIcons.append(starStarIcon)
            else:
                kwIcon = icon.ArgAssignIcon(window)
                kwIcon.replaceChild(icon.IdentifierIcon(key, window), 'leftArg')
                kwIcon.replaceChild(valueIcon, 'rightArg')
                argIcons.append(kwIcon)
        topIcon = makeIcons(func, window, x, y)
        parentIcon = icon.findLastAttrIcon(topIcon)
        parentIcon.replaceChild(callIcon, "attrIcon")
        callIcon.insertChildren(argIcons, "argIcons", 0)
        return topIcon
    if iconClass is icon.UnaryOpIcon:
        topIcon = iconClass(parsedExpr[1], window, (x, y))
        topIcon.replaceChild(makeIcons(parsedExpr[2], window, x, y), "argIcon")
        return topIcon
    if iconClass in (icon.StarIcon, icon.StarStarIcon, icon.YieldFromIcon,
     icon.AwaitIcon):
        topIcon = iconClass(window, (x, y))
        topIcon.replaceChild(makeIcons(parsedExpr[1], window, x, y), "argIcon")
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
    if iconClass is icon.DictIcon:
        topIcon = iconClass(window, location=(x, y))
        argIcons = []
        values = parsedExpr[2]
        for i, key in enumerate(parsedExpr[1]):
            value = values[i]
            if key is None:
                starStar = icon.StarStarIcon(window, location=(x,y))
                starStar.replaceChild(makeIcons(value, window, x, y), "argIcon")
                argIcons.append(starStar)
            else:
                dictElem = icon.DictElemIcon(window, location=(x,y))
                dictElem.replaceChild(makeIcons(key, window, x, y), "leftArg")
                dictElem.replaceChild(makeIcons(value, window, x, y), "rightArg")
                argIcons.append(dictElem)
        topIcon.insertChildren(argIcons, "argIcons", 0)
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
    if iconClass is icon.AugmentedAssignIcon:
        assignIcon = iconClass(parsedExpr[2], window, (x, y))
        targetIcon = makeIcons(parsedExpr[1], window, x, y)
        assignIcon.replaceChild(targetIcon, "targetIcon")
        if parsedExpr[3][0] is icon.TupleIcon:
            valueIcons = [makeIcons(v, window, x, y) for v in parsedExpr[3][1:]]
            assignIcon.insertChildren(valueIcons, "values", 0)
        else:
            assignIcon.replaceChild(makeIcons(parsedExpr[3], window, x, y), "values_0")
        return assignIcon
    if iconClass in (icon.ReturnIcon, icon.YieldIcon):
        topIcon = iconClass(window, (x, y))
        if parsedExpr[1] is None:
            return topIcon
        if parsedExpr[1][0] is icon.TupleIcon:
            valueIcons = [makeIcons(v, window, x, y) for v in parsedExpr[1][1:]]
            topIcon.insertChildren(valueIcons, "values", 0)
        else:
            topIcon.replaceChild(makeIcons(parsedExpr[1], window, x, y), "values_0")
        return topIcon
    if iconClass is icon.DelIcon:
        topIcon = iconClass(window, (x, y))
        targets = [makeIcons(t, window, x, y) for t in parsedExpr[1]]
        topIcon.insertChildren(targets, "values", 0)
        return topIcon
    if iconClass is icon.WithIcon:
        isAsync, withItems = parsedExpr[1:]
        topIcon = iconClass(isAsync, window=window, location=(x, y))
        for idx, (contextExpr, optVars) in enumerate(withItems):
            contextIcon = makeIcons(contextExpr, window, x, y)
            if optVars is None:
                topIcon.insertChild(contextIcon, "values", idx)
            else:
                asIcon = icon.WithAsIcon(window)
                asIcon.replaceChild(contextIcon, "leftArg")
                asIcon.replaceChild(makeIcons(optVars, window, x, y), "rightArg")
                topIcon.insertChild(asIcon, "values", idx)
        return topIcon
    if iconClass in (icon.GlobalIcon, icon.NonlocalIcon):
        topIcon = iconClass(window, (x, y))
        nameIcons = [icon.IdentifierIcon(name, window, (x,y)) for name in parsedExpr[1]]
        topIcon.insertChildren(nameIcons, "values", 0)
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
        if parsedExpr[1][0] is not None:
            subscriptIcon.replaceChild(makeIcons(parsedExpr[1][0], window, x, y),
                "indexIcon")
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
    if iconClass == "comprehension":
        cprhType, tgt, key, generators = parsedExpr[1:]
        topIcon = cprhType(window=window, location=(x, y))
        if key is None:
            topIcon.replaceChild(makeIcons(tgt, window, x, y), 'argIcons_0')
        else:
            dictElem = icon.DictElemIcon(window)
            dictElem.replaceChild(makeIcons(key, window, x, y), "leftArg")
            dictElem.replaceChild(makeIcons(tgt, window, x, y), "rightArg")
            topIcon.replaceChild(dictElem, 'argIcons_0')
        clauseIdx = 0
        for tgt, iter, ifs, isAsync in generators:
            forIcon = icon.CprhForIcon(isAsync, window)
            if tgt[0] is icon.TupleIcon:
                tgtIcons = [makeIcons(t, window, x, y) for t in tgt[1:]]
                forIcon.insertChildren(tgtIcons, "targets", 0)
            else:
                forIcon.insertChild(makeIcons(tgt, window, x, y), "targets", 0)
            forIcon.replaceChild(makeIcons(iter, window, x, y), 'iterIcon')
            topIcon.insertChild(forIcon, "cprhIcons", clauseIdx)
            clauseIdx += 1
            for i in ifs:
                ifIcon = icon.CprhIfIcon(window)
                testIcon = makeIcons(i, window, x, y)
                ifIcon.replaceChild(testIcon, 'testIcon')
                topIcon.insertChild(ifIcon, "cprhIcons", clauseIdx)
                clauseIdx += 1
        return topIcon
    if iconClass == "set":
        topIcon = icon.DictIcon(window, (x, y))
        childIcons = [makeIcons(pe, window, x, y) for pe in parsedExpr[1]]
        topIcon.insertChildren(childIcons, "argIcons", 0)
        return topIcon
    if iconClass is icon.WhileIcon:
        topIcon = iconClass(window=window, location=(x, y))
        topIcon.replaceChild(makeIcons(parsedExpr[1], window, x, y), 'condIcon')
        return topIcon
    if iconClass is icon.ForIcon:
        isAsync, tgt, iters = parsedExpr[1:]
        topIcon = iconClass(isAsync, window=window, location=(x, y))
        if tgt[0] is icon.TupleIcon:
            tgtIcons = [makeIcons(t, window, x, y) for t in tgt[1:]]
            topIcon.insertChildren(tgtIcons, "targets", 0)
        else:
            topIcon.replaceChild(makeIcons(tgt, window, x, y), "targets_0")
        if iters[0] is icon.TupleIcon:
            iterIcons = [makeIcons(i, window, x, y) for i in iters[1:]]
            topIcon.insertChildren(iterIcons, "iterIcons", 0)
        else:
            topIcon.replaceChild(makeIcons(iters, window, x, y), "iterIcons_0")
        return topIcon
    if iconClass is icon.IfIcon:
        topIcon = iconClass(window=window, location=(x, y))
        topIcon.replaceChild(makeIcons(parsedExpr[1], window, x, y), 'condIcon')
        return topIcon
    if iconClass is icon.ClassDefIcon:
        name, bases, kwds = parsedExpr[1:]
        hasArgs = len(bases) + len(kwds) > 0
        topIcon = iconClass(hasArgs, window=window)
        nameIcon = icon.IdentifierIcon(name, window)
        topIcon.replaceChild(nameIcon, 'nameIcon')
        baseIcons = [makeIcons(base, window, x, y) for base in bases]
        topIcon.insertChildren(baseIcons, "argIcons", 0)
        kwdIcons = []
        for idx, (kwd, value) in enumerate(kwds):
            argAssignIcon = icon.ArgAssignIcon(window)
            kwdIcon = icon.IdentifierIcon(kwd, window)
            valueIcon = makeIcons(value, window, x, y)
            argAssignIcon.replaceChild(kwdIcon, 'leftArg')
            argAssignIcon.replaceChild(valueIcon, 'rightArg')
            kwdIcons.append(argAssignIcon)
        topIcon.insertChildren(kwdIcons, "argIcons", len(baseIcons))
        return topIcon
    if iconClass is icon.DefIcon:
        isAsync, name, args, nPosOnly, defaults, varArg, kwOnlyArgs, kwDefaults, kwArg =\
         parsedExpr[1:]
        defIcon = iconClass(isAsync, window=window, location=(x, y))
        nameIcon = icon.IdentifierIcon(name, window)
        defIcon.replaceChild(nameIcon, 'nameIcon')
        if len(defaults) < len(args):
            # Weird rule in defaults list for ast that defaults can be shorter than args
            defaults = ([None] * (len(args) - len(defaults))) + defaults
        numArgs = 0
        for i, arg in enumerate(args):
            default = defaults[i]
            argNameIcon = icon.IdentifierIcon(arg, window)
            if nPosOnly != 0 and numArgs == nPosOnly:
                posOnlyMarker = icon.PosOnlyMarkerIcon(window=window)
                defIcon.insertChild(posOnlyMarker, 'argIcons', numArgs)
                numArgs += 1
            if default is None:
                defIcon.insertChild(argNameIcon, 'argIcons', numArgs)
            else:
                defaultIcon = makeIcons(default, window, x, y)
                argAssignIcon = icon.ArgAssignIcon(window)
                argAssignIcon.replaceChild(argNameIcon, 'leftArg')
                argAssignIcon.replaceChild(defaultIcon, 'rightArg')
                defIcon.insertChild(argAssignIcon, "argIcons", numArgs)
            numArgs += 1
        if varArg is not None:
            argNameIcon = icon.IdentifierIcon(varArg, window)
            starIcon = icon.StarIcon(window)
            starIcon.replaceChild(argNameIcon, 'argIcon')
            defIcon.insertChild(starIcon, 'argIcons', numArgs)
            numArgs += 1
        if len(kwOnlyArgs) > 0 and varArg is None:
            defIcon.insertChild(icon.StarIcon(window), 'argIcons', numArgs)
            numArgs += 1
        for i, arg in enumerate(kwOnlyArgs):
            default = kwDefaults[i]
            argNameIcon = icon.IdentifierIcon(arg, window)
            if default is None:
                defIcon.insertChild(argNameIcon, 'argIcons', i)
            else:
                defaultIcon = makeIcons(default, window, x, y)
                argAssignIcon = icon.ArgAssignIcon(window)
                argAssignIcon.replaceChild(argNameIcon, 'leftArg')
                argAssignIcon.replaceChild(defaultIcon, 'rightArg')
                defIcon.insertChild(argAssignIcon, "argIcons", numArgs + i)
        numArgs += len(kwOnlyArgs)
        if kwArg is not None:
            argNameIcon = icon.IdentifierIcon(kwArg, window)
            starStarIcon = icon.StarStarIcon(window)
            starStarIcon.replaceChild(argNameIcon, 'argIcon')
            defIcon.insertChild(starStarIcon, 'argIcons', numArgs)
        return defIcon
    return icon.TextIcon("**Internal Parse Error**", window, (x,y))
