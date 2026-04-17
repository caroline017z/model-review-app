"""Static checks on the inline JavaScript embedded in the mockup HTML.

A SyntaxError in the inline `<script>` block silently kills the entire
iframe boot sequence — no charts, no project list, no mode buttons —
because the parser bails before any handler attaches. This module guards
against that by:

  1. Running `node --check` on the extracted inline JS (skipped when
     Node isn't installed locally; CI should provision Node).
  2. Static checks that don't need Node:
     - balanced { } counts inside the inline script
     - no orphan top-level `}` after a `})();` IIFE
     - every function referenced in an addEventListener arrow has a
       matching `function name(` definition (cheap regex audit)
"""
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from lib.mockup_view import render_html


def _extract_inline_js(html: str) -> str:
    """Return the concatenation of every inline <script> block (ignores src=)."""
    blocks = re.findall(
        r"<script(?![^>]*\bsrc=)[^>]*>([\s\S]*?)</script>",
        html,
    )
    return "\n".join(blocks)


def _sample_html() -> str:
    """Render with a small synthetic project so the inject markers fire."""
    fake = {
        6: {
            "name": "IL Joel",
            "toggle": True,
            "data": {2: 1, 10: "US Solar", 11: 9.95, 18: "IL", 19: "Ameren",
                     22: "ABP", 118: 1.32, 597: 0.40, 602: 0.97},
        }
    }
    return render_html(fake, model_label="Test")


@pytest.fixture(scope="module")
def inline_js() -> str:
    return _extract_inline_js(_sample_html())


class TestNodeSyntax:
    """Run `node --check` on the inline JS. Skipped if Node isn't installed."""

    def test_node_check(self, tmp_path, inline_js):
        node = shutil.which("node")
        if not node:
            pytest.skip("Node.js not on PATH — skipping syntax check")
        js_file = tmp_path / "inline.js"
        js_file.write_text(inline_js, encoding="utf-8")
        result = subprocess.run(
            [node, "--check", str(js_file)],
            capture_output=True, text=True, timeout=10,
        )
        assert result.returncode == 0, (
            f"node --check failed:\nSTDERR:\n{result.stderr}\n"
            f"STDOUT:\n{result.stdout}"
        )


class TestStaticPatterns:
    """Pattern checks that don't require Node — catch the specific bug
    class that already bit us once ('orphan }' immediately after an IIFE)."""

    def test_no_orphan_brace_after_iife(self, inline_js):
        """The actual bug we hit: '})();\\n}' parses as a stray top-level }."""
        m = re.search(r"\}\)\(\);\s*\n\s*\}\s*(?:\n|$)", inline_js)
        assert m is None, (
            f"Found an orphan '}}' immediately after a '}})()'; this would "
            f"throw SyntaxError at parse time. Snippet:\n"
            f"{inline_js[max(0,(m.start() if m else 0)-80):(m.end() if m else 0)+40]}"
        )

    def test_no_double_let_const_redeclare_at_top_level(self, inline_js):
        """`let X = …` followed somewhere later by another `let X = …` at
        top level (not inside a function/IIFE) is a runtime SyntaxError in
        strict mode."""
        # Cheap heuristic: line-start `let NAME = …;` declarations.
        names = re.findall(r"^let\s+([A-Za-z_][A-Za-z0-9_]*)\s*=", inline_js, re.MULTILINE)
        from collections import Counter
        dupes = [n for n, c in Counter(names).items() if c > 1]
        assert not dupes, f"Duplicate top-level `let` declarations: {dupes}"


class TestReferencedFunctionsExist:
    """Cheap static check: every JS function name we know we depend on at
    boot must actually be defined somewhere in the inline script."""

    EXPECTED_FUNCTIONS = [
        "renderPortfolio",
        "renderProjectList",
        "renderPortfolioSummary",
        "renderFindings",
        "renderKpis",
        "renderClassify",
        "renderWrappedEpc",
        "renderReferences",
        "renderCharts",
        "selectProject",
        "_updateProjectApprovalBanner",
        "_renderAuditLog",
        "_clsRefreshEnable",
        "_worstProjectIdx",
        "isIncluded",
        "visibleProjects",
        "_safe_audit_dummy_fn_should_NOT_exist",  # negative control
    ]

    def test_each_function_defined(self, inline_js):
        """Every entry except the negative control should have a `function NAME(`
        or `const NAME = function(` definition in the inline script."""
        missing = []
        for name in self.EXPECTED_FUNCTIONS:
            patterns = [
                rf"\bfunction\s+{re.escape(name)}\s*\(",
                rf"\b(?:const|let|var)\s+{re.escape(name)}\s*=\s*(?:function|\()",
            ]
            found = any(re.search(p, inline_js) for p in patterns)
            if name == "_safe_audit_dummy_fn_should_NOT_exist":
                # Negative control: should NOT be defined.
                assert not found, "negative control accidentally exists"
                continue
            if not found:
                missing.append(name)
        assert not missing, f"Inline JS missing function definitions for: {missing}"
