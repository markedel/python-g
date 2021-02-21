import iconsites
import icon
import opicons
import listicons
import blockicons
import subscripticon
import parenicon
import entryicon

def _reduceOperatorStack(operatorStack, operandStack):
    """This is the inner component of reorderArithExpr (see below).  Pop a single operator
    off of the operator stack, link it with operands popped from the operand stack, and
    push the result on the operand stack."""
    stackOp = operatorStack.pop()
    if isinstance(stackOp, OpenParenToken):
        stackOp.arg = operandStack.pop()
    elif isinstance(stackOp, BinaryOpToken):
        stackOp.rightArg = operandStack.pop()
        stackOp.leftArg = operandStack.pop()
    elif isinstance(stackOp, UnaryOpToken):
        stackOp.arg = operandStack.pop()
    else:
        print('_reduceOperatorStack: unexpected icon on operator stack')
    operandStack.append(stackOp)

def reorderArithExpr(changedIcon, closeParenAt=None):
    """Reorders the arithmetic operators surrounding changed icon to agree with the text
    of the connected icons.  Because the icon representation reflects the hierarchy of
    operations, as opposed to the precedence and associativity of operators that the user
    types, changing an operator to one of a different precedence or adding or removing a
    paren, can drastically change what the expression means to the user.  This routine
    rearranges the hierarchy to match what the user sees.  changedIcon should specify an
    icon involved in the change.  If the changed icon is a paren/bracket/brace that needs
    to be closed, use closeParenAt to specify the rightmost icon to be enclosed (if
    successful, this function will close the paren/bracket/brace of changedIcon)."""
    topNode = highestAffectedExpr(changedIcon)
    topNodeParent = topNode.parent()
    topNodeParentSite = None if topNodeParent is None else topNodeParent.siteOf(topNode)
    if changedIcon.__class__ in (listicons.ListIcon, listicons.DictIcon,
     listicons.CallIcon, blockicons.DefIcon, subscripticon.SubscriptIcon) or \
     isinstance(changedIcon, blockicons.ClassDefIcon) and changedIcon.argList:
        allowedNonParen = OpenParenToken(changedIcon)
    else:
        allowedNonParen = None
    operatorStack = []
    operandStack = []
    # Loop left to right over the expression below topNode, assembling a tree containing
    # the icons that may need to be re-linked organized in the form that the icons will
    # need to take.
    for op in tuple(traverseExprLeftToRight(topNode, allowedNonParen, closeParenAt)):
        if isinstance(op, BinaryOpToken):
            # Binary operation.  Check if left operand can be reduced
            while len(operatorStack) > 0:
                stackOp = operatorStack[-1]
                if isinstance(stackOp, OpenParenToken) or (
                 stackOp.ic.precedence < op.ic.precedence or
                 stackOp.ic.precedence == op.ic.precedence and op.ic.rightAssoc()):
                    break
                _reduceOperatorStack(operatorStack, operandStack)
            operatorStack.append(op)
        elif isinstance(op, UnaryOpToken):
            # It's an operator, but the only operand is on the right
            operatorStack.append(op)
        elif isinstance(op, OpenParenToken):
            if op.parenIcon is changedIcon and closeParenAt:
                op.closed = True
            operatorStack.append(op)
        elif isinstance(op, CloseParenToken):
            while len(operatorStack) > 0:
                stackOp = operatorStack[-1]
                _reduceOperatorStack(operatorStack, operandStack)
                if isinstance(stackOp, OpenParenToken) and stackOp.closed:
                    if stackOp.parenIcon is not op.parenIcon:
                        # If parens have shifted, any attributes attached to the parens
                        # also need to shift.  Likewise for attached cursor & entry icon
                        if stackOp is allowedNonParen:
                            print('reorderArithExpr did not close matching brace/bracket')
                        stackOp.endParenAttr = None if op.parenIcon is None else \
                                op.parenIcon.childAt('attrIcon')
                        stackOp.endParenIc = op.parenIcon
                        cursor = stackOp.parenIcon.window.cursor
                        stackOp.takeCursor = cursor.type == "icon" and \
                         cursor.site == 'attrIcon' and cursor.icon is stackOp.parenIcon
                        stackOp.takeEntryIcon = closeParenAt and op.parenIcon is None
                    if stackOp.closed:
                        break  # Stop reducing once a matching paren is processed
        else:
            # Everything else is considered an operand
            operandStack.append(op)
    # Upon reaching the end of the expression, reduce all of the operators remaining in
    # the operator stack.
    while len(operatorStack) > 0:
        _reduceOperatorStack(operatorStack, operandStack)
    if len(operandStack) != 1:
        print("reorderArithExpr failed to converge")
        return topNode
    # print('before reorder') ; icon.dumpHier(topNode)
    # Requested paren can now be safely closed
    if closeParenAt:
        changedIcon.close()
    # Re-link the icons to the new expression form based on the token tree
    # print('token tree') ; dumpTok(operandStack[0])
    newTopNode = relinkExprFromTokens(operandStack[0])
    # print('after reorder') ; icon.dumpHier(newTopNode)
    # If the top node of the expression changed, re-link that to its parent
    if newTopNode is not topNode:
        if topNodeParent is None:
            newTopNode.replaceChild(None, 'output')
            topNode.window.replaceTop(topNode, newTopNode)
        else:
            topNodeParent.replaceChild(newTopNode, topNodeParentSite)
    # Parent links were not necessarily intact when icons were re-linked, and even though
    # the icons themselves get marked dirty, they won't be found unless the page is
    # marked as well.  Now that everything is back in place, mark the top icon again.
    newTopNode.markLayoutDirty()
    return newTopNode

def highestAffectedExpr(changedIcon):
    topCoincidentIcon = iconsites.highestCoincidentIcon(changedIcon)
    for ic in topCoincidentIcon.parentage(includeSelf=True):
        parent = ic.parent()
        if parent is None:
            return ic  # ic is at top level
        site = parent.siteOf(ic)
        siteType = parent.typeOf(site)
        if siteType == "input" and parent.__class__ not in (opicons.BinOpIcon,
         opicons.UnaryOpIcon, parenicon.CursorParenIcon):
            return ic  # Everything other than arithmetic expressions encloses args

def traverseExprLeftToRight(topNode, allowedNonParen=None, closeParenAfter=None):
    """Traverse an expression from left to right returning "token" objects containing.
    one or more icons.  Note that this is not a fully general left to right traversal,
    but one specifically tailored to reorderArithExpr which operates only within the
    bounds of a changed expression, skipping over anything contained within icons other
    than arithmetic operations, cursor parens, and a single non-arithmetic paren/bracket/
    brace being modified (allowedNonParen).  If closeParenAfter is specified, emit an
    additional CloseParenToken when that icon is encountered in the traversal."""
    representedIcons = (topNode, )
    if topNode is None:
        yield MissingArgToken()
    elif isinstance(topNode, opicons.BinOpIcon):
        if topNode.hasParens:
            yield OpenParenToken(topNode)
        yield from traverseExprLeftToRight(topNode.leftArg(), allowedNonParen,
         closeParenAfter)
        yield BinaryOpToken(topNode)
        yield from traverseExprLeftToRight(topNode.rightArg(), allowedNonParen,
         closeParenAfter)
        if topNode.hasParens:
            yield CloseParenToken(topNode)
    elif isinstance(topNode, opicons.UnaryOpIcon):
        yield UnaryOpToken(topNode)
        yield from traverseExprLeftToRight(topNode.arg(), allowedNonParen,
         closeParenAfter)
    elif allowedNonParen is not None and topNode is allowedNonParen.ic:
        yield allowedNonParen
        parenContent = allowedNonParen.parenIcon.childAt(allowedNonParen.contentSite)
        yield from traverseExprLeftToRight(parenContent, allowedNonParen, closeParenAfter)
        representedIcons = allowedNonParen.representedIcons
    elif isinstance(topNode, parenicon.CursorParenIcon):
        openParenOp = OpenParenToken(topNode)
        yield openParenOp
        yield from traverseExprLeftToRight(topNode.childAt('argIcon'), allowedNonParen,
         closeParenAfter)
        if topNode.closed:
            yield CloseParenToken(topNode)
        representedIcons = openParenOp.representedIcons
    else:
        # Anything that is not a binary operator or a cursor paren can be treated as a
        # unit rather than descending in to it.
        yield OperandToken(topNode)
        representedIcons = topNode.traverse(includeSelf=True)
    # If we're processing a newly entered close-paren, generate a CloseParenToken for it
    # after the icon indicated by closeParenAfter is emitted.
    if closeParenAfter is not None and closeParenAfter in representedIcons:
        yield CloseParenToken(None)

class OpenParenToken:
    """This class wraps various types of parentheses-like icon (brackets, braces,
    etc.) in the operator stack to simplify paren handling in reorderArithExpr.  Most
    importantly, it allows reorderArithExpr to treat an entire chain of attributes
    leading to paren types that are connected to attribute sites (CallIcon and
    SubscriptIcon) as a unit, in the same manner it treats cursor parens, lists,
    and dicts."""
    def __init__(self, parenIcon):
        self.representedIcons = [parenIcon]
        self.parenIcon = parenIcon
        if parenIcon.hasSite('attrOut'):
            self.ic = icon.findAttrOutputSite(parenIcon)
            for parent in parenIcon.parentage():
                self.representedIcons.append(parent)
                if parent is self.ic:
                    break
        else:
            self.ic = parenIcon
        if parenIcon is not None and parenIcon.hasSite('attrIcon'):
            attrIcon = parenIcon.childAt('attrIcon')
            if attrIcon is not None:
                self.representedIcons += list(attrIcon.traverse())
        if isinstance(parenIcon, opicons.BinOpIcon):
            self.contentSite = None
        elif parenIcon.hasSite('argIcons_0'):
            self.contentSite = 'argIcons_0'
        elif isinstance(parenIcon, subscripticon.SubscriptIcon):
            self.contentSite = 'indexIcon'
        else:
            self.contentSite = 'argIcon'
        self.closed = isinstance(self.parenIcon, opicons.BinOpIcon) or \
                self.parenIcon.closed
        self.arg = None
        self.endParenAttr = None
        self.endParenIc = None
        self.takeCursor = False
        self.takeEntryIcon = False

class CloseParenToken:
    """Represent an end-paren in the operator stack"""
    def __init__(self, parenIcon):
        self.parenIcon = parenIcon

class BinaryOpToken:
    def __init__(self, ic):
        self.ic = ic
        self.leftArg = None
        self.rightArg = None

class UnaryOpToken:
    def __init__(self, ic):
        self.ic = ic
        self.arg = None

class OperandToken:
    """Represents a tree of icons that are not part of the arithmetic expression being
    reordered (the tree can contain other arithmetic expressions, if they are separated
    from it by something other than arithmetic operators and grouping parens)."""
    def __init__(self, ic):
        self.ic = ic
        self.argTree = None

class MissingArgToken:
    pass

def relinkExprFromTokens(token, parentIc=None, parentSite=None):
    """reorderArithExpr re-parses arithmetic expressions to a tree of token objects
    containing the icons being reordered.  This routine does the actual rewiring of the
    icon structure per the token tree.  Reordering the icons is postponed until after
    all of the parsing is complete so that parens can be re-established based on proper
    precedence and associativity of parent operations (and allowing it to safely back
    out if parsing fails). Rather than filtering out redundant parentheses,
    reorderArithExpr works hard to preserve the exact paren counts that the user saw
    before making the change, possibly resulting auto-parens becoming cursor parens and
    visa versa."""
    if isinstance(token, OperandToken):
        return token.ic
    elif isinstance(token, MissingArgToken):
        return None
    elif isinstance(token, UnaryOpToken):
        arg = relinkExprFromTokens(token.arg, token.ic, 'argIcon')
        if arg.parent() is not token.ic:
            token.ic.replaceChild(arg, 'argIcon')
        return token.ic
    elif isinstance(token, BinaryOpToken):
        leftArg = relinkExprFromTokens(token.leftArg, token.ic, 'leftArg')
        rightArg = relinkExprFromTokens(token.rightArg, token.ic, 'rightArg')
        if token.ic.leftArg() is not leftArg:
            token.ic.replaceChild(leftArg, 'leftArg')
        if token.ic.rightArg() is not rightArg:
            token.ic.replaceChild(rightArg, 'rightArg')
        return token.ic
    elif isinstance(token, OpenParenToken):
        if token.closed and isinstance(token.arg, BinaryOpToken) and \
                opicons.needsParens(token.arg.ic, parentIc, parentSite=parentSite):
            # Binary op child icon will provide its own auto-parens
            parenIc = relinkExprFromTokens(token.arg, parentIc, parentSite)
            outIc = parenIc
            if isinstance(token.parenIcon, parenicon.CursorParenIcon):
                # a cursor paren icon is being deleted in favor of the binOp parens.
                # Transfer attributes and cursor from deleted paren
                deletedIconAttr = token.parenIcon.childAt('attrIcon')
                if deletedIconAttr:
                    parenIc.replaceChild(deletedIconAttr, 'attrIcon')
                    if isinstance(deletedIconAttr, entryicon.EntryIcon):
                        deletedIconAttr.attachedIcon = parenIc
                cursor = parenIc.window.cursor
                if cursor.type == 'icon' and cursor.icon is token.parenIcon:
                    cursorSite = 'leftArg' if cursor.site == 'argIcon' else 'attrIcon'
                    cursor.setToIconSite(parenIc, cursorSite)
        else:
            # Add parens around argument using existing icon if possible.  If not
            # (because parens were bin op auto-parens), create a new cursor paren
            if isinstance(token.ic, opicons.BinOpIcon):
                parenIc = parenicon.CursorParenIcon(window=token.ic.window,
                        closed=token.closed)
                contentSite = 'argIcon'
                outIc = parenIc
            else:
                parenIc = token.parenIcon
                contentSite = token.contentSite
                outIc = token.ic
            arg = relinkExprFromTokens(token.arg, parenIc, contentSite)
            if parenIc.childAt(contentSite) is not arg:
                parenIc.replaceChild(arg, contentSite)
        # If parens were shifted and the original parens had an attribute, transfer the
        # attribute to the icon taking its place.  EntryIcon also has attachedIcon field.
        if token.endParenAttr is not None and \
                token.endParenAttr is not parenIc.childAt('attrIcon'):
            if token.endParenIc.childAt('attrIcon') is token.endParenAttr:
                token.endParenIc.replaceChild(None, 'attrIcon')
            parenIc.replaceChild(token.endParenAttr, 'attrIcon')
            if isinstance(token.endParenAttr, entryicon.EntryIcon):
                token.endParenAttr.attachedIcon = parenIc
        # Move cursor and entry icon if directed
        if token.takeCursor:
            parenIc.window.cursor.setToIconSite(token.endParenAttr, 'attrIcon')
        if token.takeEntryIcon:
            entryIcon = parenIc.window.entryIcon
            if entryIcon is not None:
                eiParent = entryIcon.parent()
                eiParent.replaceChild(None, eiParent.siteOf(entryIcon))
                parenIc.replaceChild(entryIcon, 'attrIcon')
                entryIcon.attachedIcon = parenIc
                entryIcon.attachedSite = 'attrIcon'
                entryIcon.attachedSiteType = 'attrIn'
        return outIc
    print('Unrecognized token in relinkExprFromTokens')
    return None

def dumpTok(token, indent=0):
    if isinstance(token, OperandToken):
        print("   " * indent, 'Operand', token.ic.textRepr())
    elif isinstance(token, MissingArgToken):
        print("   " * indent, "Missing Arg")
    elif isinstance(token, UnaryOpToken):
        print("   " * indent, "UnaryOp", token.ic.dumpName())
        dumpTok(token.arg, indent+1)
    elif isinstance(token, BinaryOpToken):
        print("   " * indent, "BinaryOp", token.ic.dumpName())
        dumpTok(token.leftArg, indent+1)
        dumpTok(token.rightArg, indent+1)
    elif isinstance(token, OpenParenToken):
        parenType = "BinOp" if isinstance(token.parenIcon, opicons.BinOpIcon) else ""
        attr = ""
        if token.endParenAttr is not None:
            attr = token.endParenAttr.dumpName() + " <- " + \
                    token.endParenIc.dumpName() + " " + str(token.endParenIc.id)
        print("   " * indent, parenType + "Paren", token.parenIcon.dumpName(),
                token.parenIcon.id, attr)
        dumpTok(token.arg, indent+1)
