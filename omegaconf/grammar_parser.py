import gc
import re
import sys
import threading
from collections import OrderedDict
from typing import Any

from . import _control
from .errors import GrammarParseError

# Import from visitor in order to check the presence of generated grammar files
# files in a single place.
from .grammar_visitor import (  # type: ignore
    OmegaConfGrammarLexer,
    OmegaConfGrammarParser,
)
from .typing import Antlr4ParserRuleContext
from .vendor.antlr4 import CommonTokenStream, InputStream  # type: ignore[attr-defined]
from .vendor.antlr4.error.ErrorListener import ErrorListener
from .vendor.antlr4.Lexer import Lexer
from .vendor.antlr4.Parser import Parser
from .vendor.antlr4.RuleContext import RuleContext
from .vendor.antlr4.Token import Token
from .vendor.antlr4.tree.Tree import TerminalNodeImpl

# Used to cache grammar objects to avoid re-creating them on each call to `parse()`.
# We use a per-thread cache to make it thread-safe.
_grammar_cache = threading.local()


def _tree_cache_weight(tree: Antlr4ParserRuleContext, limit: int) -> int | None:
    # Count tree-owned allocations, excluding the parser/lexer already retained
    # by this thread's grammar cache. Shared objects are counted once per entry.
    pending: list[Any] = [tree]
    seen: set[int] = set()
    weight = 256  # Cache key and entry bookkeeping allowance.
    while pending:
        obj = pending.pop()
        if id(obj) in seen or isinstance(obj, (type, Parser, Lexer)):
            continue
        seen.add(id(obj))
        if not isinstance(
            obj,
            (
                RuleContext,
                TerminalNodeImpl,
                Token,
                InputStream,
                list,
                tuple,
                dict,
                str,
                bytes,
                int,
                float,
                type(None),
            ),
        ):
            return None
        size = sys.getsizeof(obj, 0)
        if size == 0:
            return None
        weight += size
        if isinstance(obj, (RuleContext, TerminalNodeImpl, Token)):
            # Avoid materializing instance dictionaries just to measure them.
            weight += 64
        if weight > limit:
            return None
        pending.extend(gc.get_referents(obj))
    return weight


class _SyntaxCache:
    def __init__(self, max_bytes: int, generation: int) -> None:
        self.entries: OrderedDict[
            tuple[str, str, str], tuple[Antlr4ParserRuleContext, int]
        ] = OrderedDict()
        self.weight = 0
        self.max_bytes = max_bytes
        self.generation = generation

    def trim(self, max_bytes: int) -> None:
        while self.weight > max_bytes:
            _, (_, weight) = self.entries.popitem(last=False)
            self.weight -= weight

    def parse(
        self, value: str, parser_rule: str, lexer_mode: str
    ) -> Antlr4ParserRuleContext:
        key = (value, parser_rule, lexer_mode)
        cached = self.entries.get(key)
        if cached is not None:
            self.entries.move_to_end(key)
            return cached[0]
        tree = parse(value, parser_rule, lexer_mode)
        weight = _tree_cache_weight(tree, min(self.max_bytes, 256 * 1024))
        if weight is not None:
            self.trim(self.max_bytes - weight)
            # Keep the entry count secondary to the memory budget.
            if len(self.entries) == 256:
                _, (_, old_weight) = self.entries.popitem(last=False)
                self.weight -= old_weight
            self.entries[key] = (tree, weight)
            self.weight += weight
        return tree


def _parse_cached(
    value: str, parser_rule: str = "configValue", lexer_mode: str = "DEFAULT_MODE"
) -> Antlr4ParserRuleContext:
    # One immutable snapshot; an in-progress operation may finish under the old
    # policy. Each thread owns its parser, LRU and accounting, including updates.
    max_bytes, generation = _control._syntax_cache_policy
    cache = getattr(_grammar_cache, "parse_trees", None)
    if cache is not None and cache.generation != generation:
        cache.max_bytes = max_bytes
        cache.generation = generation
        cache.trim(max_bytes)
    if max_bytes == 0 or type(value) is not str:
        return parse(value, parser_rule, lexer_mode)
    if cache is None:
        cache = _grammar_cache.parse_trees = _SyntaxCache(max_bytes, generation)
    return cache.parse(value, parser_rule, lexer_mode)


# Build regex pattern to efficiently identify typical interpolations.
# See test `test_match_simple_interpolation_pattern` for examples.
_config_key = r"[$\w]+"  # foo, $0, $bar, $foo_$bar123$
_key_maybe_brackets = f"{_config_key}|\\[{_config_key}\\]"  # foo, [foo], [$bar]
_node_access = f"\\.{_key_maybe_brackets}"  # .foo, [foo], [$bar]
_node_path = f"(\\.)*({_key_maybe_brackets})({_node_access})*"  # [foo].bar, .foo[bar]
_node_inter = f"\\${{\\s*{_node_path}\\s*}}"  # node interpolation ${foo.bar}
_id = "[a-zA-Z_][\\w\\-]*"  # foo, foo_bar, foo-bar, abc123
_resolver_name = f"({_id}(\\.{_id})*)?"  # foo, ns.bar3, ns_1.ns_2.b0z
_arg = r"[a-zA-Z_0-9/\-\+.$%*@?|]+"  # string representing a resolver argument
_args = f"{_arg}(\\s*,\\s*{_arg})*"  # list of resolver arguments  # noqa: E231
_resolver_inter = (
    f"\\${{\\s*{_resolver_name}\\s*:\\s*{_args}?\\s*}}"  # ${foo:bar}  # noqa: E231
)
_inter = f"({_node_inter}|{_resolver_inter})"  # any kind of interpolation
_outer = "([^$]|\\$(?!{))+"  # any character except $ (unless not followed by {)
SIMPLE_INTERPOLATION_PATTERN: re.Pattern[str] = re.compile(
    f"({_outer})?({_inter}({_outer})?)+$", flags=re.ASCII
)
# NOTE: SIMPLE_INTERPOLATION_PATTERN must not generate false positive matches:
# it must not accept anything that isn't a valid interpolation (per the
# interpolation grammar defined in `omegaconf/grammar/*.g4`).

# ParserRuleContext: TypeAlias = ParserRuleContext


class OmegaConfErrorListener(ErrorListener):
    def syntaxError(
        self,
        recognizer: Any,
        offendingSymbol: Any,
        line: Any,
        column: Any,
        msg: Any,
        e: Any,
    ) -> None:
        raise GrammarParseError(str(e) if msg is None else msg) from e

    def reportAmbiguity(
        self,
        recognizer: Any,
        dfa: Any,
        startIndex: Any,
        stopIndex: Any,
        exact: Any,
        ambigAlts: Any,
        configs: Any,
    ) -> None:
        raise GrammarParseError("ANTLR error: Ambiguity")  # pragma: no cover

    def reportAttemptingFullContext(
        self,
        recognizer: Any,
        dfa: Any,
        startIndex: Any,
        stopIndex: Any,
        conflictingAlts: Any,
        configs: Any,
    ) -> None:
        # Note: for now we raise an error to be safe. However this is mostly a
        # performance warning, so in the future this may be relaxed if we need
        # to change the grammar in such a way that this warning cannot be
        # avoided (another option would be to switch to SLL parsing mode).
        raise GrammarParseError(
            "ANTLR error: Attempting Full Context"
        )  # pragma: no cover

    def reportContextSensitivity(
        self,
        recognizer: Any,
        dfa: Any,
        startIndex: Any,
        stopIndex: Any,
        prediction: Any,
        configs: Any,
    ) -> None:
        raise GrammarParseError("ANTLR error: ContextSensitivity")  # pragma: no cover


def parse(
    value: str, parser_rule: str = "configValue", lexer_mode: str = "DEFAULT_MODE"
) -> Antlr4ParserRuleContext:
    """
    Parse interpolated string `value` (and return the parse tree).
    """
    l_mode = getattr(OmegaConfGrammarLexer, lexer_mode)
    istream = InputStream(value)

    cached = getattr(_grammar_cache, "data", None)
    if cached is None:
        error_listener = OmegaConfErrorListener()
        lexer = OmegaConfGrammarLexer(istream)
        lexer.removeErrorListeners()
        lexer.addErrorListener(error_listener)
        lexer.mode(l_mode)
        token_stream = CommonTokenStream(lexer)
        parser = OmegaConfGrammarParser(token_stream)
        parser.removeErrorListeners()
        parser.addErrorListener(error_listener)

        # The two lines below could be enabled in the future if we decide to switch
        # to SLL prediction mode. Warning though, it has not been fully tested yet!
        # from omegaconf.vendor.antlr4 import PredictionMode
        # parser._interp.predictionMode = PredictionMode.SLL

        # Note that although the input stream `istream` is implicitly cached within
        # the lexer, it will be replaced by a new input next time the lexer is re-used.
        _grammar_cache.data = lexer, token_stream, parser

    else:
        lexer, token_stream, parser = cached
        # Replace the old input stream with the new one.
        lexer.inputStream = istream
        # Initialize the lexer / token stream / parser to process the new input.
        lexer.mode(l_mode)
        token_stream.setTokenSource(lexer)
        parser.reset()

    try:
        return getattr(parser, parser_rule)()  # type: ignore
    except Exception as exc:
        if type(exc) is Exception and str(exc) == "Empty Stack":
            # This exception is raised by antlr when trying to pop a mode while
            # no mode has been pushed. We convert it into an `GrammarParseError`
            # to facilitate exception handling from the caller.
            raise GrammarParseError("Empty Stack")
        else:
            raise
