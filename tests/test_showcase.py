"""Acceptance boundaries for a public preview without the local product runtime."""
import builtins
import hashlib
import json
import re
from html import unescape
from datetime import timedelta
from pathlib import Path
import unittest
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

from finscope.showcase_data import (END, START, article_label, candidate_groups,
                                   examples, graph, graph_overview, select, word_cloud_terms)


from finscope.showcase_theme import NAV_KEYS

ROOT = Path(__file__).resolve().parents[1]


def navigate(app, page):
    return app.button(key=NAV_KEYS[page]).click().run()


def article_widget(app, key):
    return next(widget for widget in app.selectbox if (widget.key or "").startswith(key + "__"))


def workflow_titles(app):
    markup = next(m.value for m in app.markdown
                  if 'aria-label="Local workflow: Settings to Dashboard"' in m.value)
    return [(int(index), unescape(title)) for index, title
            in re.findall(r'<li data-workflow-step="(\d+)">.*?<h3>(.*?)</h3>', markup, re.S)]


class ShowcaseTests(unittest.TestCase):
    def setUp(self):
        original_import = builtins.__import__
        forbidden = ("torch", "transformers", "huggingface_hub", "finscope.api_sources",
                     "finscope.product_ui", "finscope.local_news", "finscope.model_assets",
                     "finscope.demo_runtime", "finscope.finbert_backend", "finscope.embedding_backend",
                     "finscope.local_worker", "finscope.settings_ui", "finscope.industry_classifier",
                     "finscope.model_providers", "finscope.media_monitor", "finscope.media_batch")

        def guarded_import(name, *args, **kwargs):
            if any(name == prefix or name.startswith(prefix + ".") for prefix in forbidden):
                raise AssertionError("Showcase attempted a local runtime import: " + name)
            return original_import(name, *args, **kwargs)

        for mocker in (
                patch("builtins.__import__", side_effect=guarded_import),
                patch("requests.sessions.Session.request", side_effect=AssertionError("Showcase attempted HTTP")),
                patch("urllib.request.urlopen", side_effect=AssertionError("Showcase attempted HTTP")),
                patch("sqlite3.connect", side_effect=AssertionError("Showcase attempted database access"))):
            mocker.start()
            self.addCleanup(mocker.stop)

    def app(self):
        app = AppTest.from_file(str(ROOT / "deploy/streamlit_app.py"), default_timeout=15).run()
        self.assertFalse(app.exception)
        return app

    def test_every_page_runs_without_providers_database_or_models(self):
        app = self.app()
        pages = list(NAV_KEYS)
        self.assertEqual({b.key for b in app.button if b.key in NAV_KEYS.values()}, set(NAV_KEYS.values()))
        self.assertFalse(any(r.key == "showcase_page" for r in app.radio))
        self.assertEqual(len(pages), 6)
        for page in pages:
            navigate(app, page)
            self.assertFalse(app.exception, page)
            self.assertFalse(app.get("file_uploader"))
            self.assertFalse(any("API key" in item.label for item in app.text_input))
            self.assertFalse(any("Prepare" in item.label or "Fetch news" in item.label
                                 or "Run real AI" in item.label for item in app.button))

    def test_display_preferences_cover_all_six_pages_with_runtime_guards(self):
        from finscope.showcase_theme import LIGHT_TOKENS, TOKENS
        for language in ("en", "zh-CN"):
            for appearance in ("dark", "light"):
                with self.subTest(language=language, appearance=appearance):
                    app = self.app()
                    app.selectbox(key="showcase_language").set_value(language).run()
                    app.radio(key="showcase_appearance").set_value(appearance).run()
                    for page in NAV_KEYS:
                        navigate(app, page)
                        self.assertFalse(app.exception, (language, appearance, page))
                        self.assertEqual(app.selectbox(key="showcase_language").value, language)
                        self.assertEqual(app.radio(key="showcase_appearance").value, appearance)
                        markup = "\n".join(m.value for m in app.markdown)
                        tokens = LIGHT_TOKENS if appearance == "light" else TOKENS
                        self.assertIn("--fs-background: " + tokens["background"], markup)
                        self.assertIn("演示数据 / 示意预览" if language == "zh-CN"
                                      else "Demo Data / Illustrative Preview", markup)
                        if page == "Dashboard Preview":
                            self.assertEqual(app.metric[0].value, "24")
                            self.assertIn("这是示意，不是模型输出" if language == "zh-CN" else "Industry intelligence",
                                          " ".join(c.value for c in app.caption) if language == "zh-CN"
                                          else " ".join(h.value for h in app.subheader))
                        if page == "Get FinScope":
                            self.assertTrue(any("--branch local --single-branch" in c.value for c in app.code))
                            self.assertTrue(any(c.value == "./launch_local.ps1 -Port 8501" for c in app.code))

    def test_switching_language_and_appearance_preserves_filters_and_article_ids(self):
        app = self.app()
        navigate(app, "Dashboard Preview")
        app.multiselect(key="preview_sectors").set_value(["Technology"]).run()
        app.multiselect(key="preview_sentiments").set_value(["Positive"]).run()
        self.assertEqual(app.metric[0].value, "2")
        chosen_dates = (START, END - timedelta(days=1))
        app.date_input(key="preview_dates").set_value(chosen_dates).run()
        app.selectbox(key="showcase_language").set_value("zh-CN").run()
        app.radio(key="showcase_appearance").set_value("light").run()
        self.assertEqual(app.multiselect(key="preview_sectors__display_zh").value, ["Technology"])
        self.assertEqual(app.multiselect(key="preview_sentiments__display_zh").value, ["Positive"])
        self.assertEqual(app.multiselect(key="preview_sectors__display_zh").options[0], "科技")
        self.assertEqual(tuple(app.date_input(key="preview_dates").value), chosen_dates)
        self.assertEqual(app.metric[0].value, "2")
        app.multiselect(key="preview_sentiments__display_zh").set_value(["Negative"]).run()
        self.assertEqual(app.metric[0].value, "1")
        app.multiselect(key="preview_sectors__display_zh").set_value(["Healthcare"]).run()
        self.assertEqual(app.multiselect(key="preview_sectors__display_zh").value, ["Healthcare"])
        self.assertEqual(app.metric[0].value, "1")
        next(b for b in app.button if b.label == "重置预览").click().run()
        self.assertEqual(app.metric[0].value, "24")
        navigate(app, "Knowledge Graph")
        app.selectbox(key="graph_company").set_value("Cedar Therapeutics").run()
        article_widget(app, "graph_article").set_value("SYN-007").run()
        app.selectbox(key="graph_cloud_word").set_value("research").run()
        self.assertIn("Research Centre Opens", article_widget(app, "graph_cloud_article").options)
        matches = next(d.value for d in app.dataframe if "完整标题" in d.value.columns)
        self.assertEqual(set(matches["标题"]), {article_label(r) for r in examples()
                                              if r.article_id in ("SYN-002", "SYN-005", "SYN-006")})
        app.selectbox(key="showcase_language").set_value("en").run()
        app.radio(key="showcase_appearance").set_value("dark").run()
        self.assertEqual(app.selectbox(key="graph_company").value, "Cedar Therapeutics")
        self.assertEqual(article_widget(app, "graph_article").value, "SYN-007")
        self.assertEqual(app.selectbox(key="graph_cloud_word").value, "research")
        self.assertFalse(app.exception)

    def test_landing_calls_to_action_and_local_installation(self):
        app = self.app()
        next(b for b in app.button if b.label == "How it works").click().run()
        self.assertEqual(app.session_state["showcase_page"], "User Guide")
        self.assertEqual(workflow_titles(app), [(1, "Settings"), (2, "Update & Analyze"),
                                               (3, "Background Worker"), (4, "Dashboard")])
        navigate(app, "Get FinScope")
        content = "\n".join(code.value for code in app.code)
        self.assertIn("requirements-local.txt", content)
        self.assertIn("streamlit run streamlit_app.py", content)
        self.assertIn("--server.address localhost --server.port 8501", content)
        self.assertNotIn("-r deploy/requirements.txt", content)
        clone_commands = [code.value for code in app.code if "git clone" in code.value]
        self.assertEqual(len(clone_commands), 2)
        for command in clone_commands:
            self.assertIn("git clone --branch local --single-branch https://github.com/DVDWK812/Finscope.git", command)
        links = {item.proto.label: item.proto.url for item in app.get("link_button")}
        self.assertEqual(links["Get the local product on GitHub"], "https://github.com/DVDWK812/Finscope/tree/local")
        self.assertEqual(links["Showcase source"], "https://github.com/DVDWK812/Finscope/tree/main")
        markup = "\n".join(m.value for m in app.markdown)
        self.assertIn("OPTIONAL LOCAL INTEGRATIONS", markup)
        self.assertIn("Local LM Studio", markup)
        self.assertNotIn("IN DEVELOPMENT", markup)
        windows = "\n".join(code.value for code in app.tabs[0].code)
        unix = "\n".join(code.value for code in app.tabs[1].code)
        self.assertEqual(sum(c.value == "./launch_local.ps1 -Port 8501" for c in app.code), 1)
        self.assertIn('aria-label="Windows launcher starts UI and worker"', markup)
        self.assertNotIn("-m streamlit run", windows)
        self.assertIn("-m finscope.local_worker", unix)
        self.assertIn("-m streamlit run", unix)
        self.assertTrue(any("macOS/Linux runtime acceptance is pending" in c.value for c in app.caption))

    def test_reviewed_guide_keeps_scope_and_verification_qualifications(self):
        app = self.app()
        navigate(app, "User Guide")
        self.assertEqual(workflow_titles(app), [(1, "Settings"), (2, "Update & Analyze"),
                                               (3, "Background Worker"), (4, "Dashboard")])
        text = "\n".join(m.value for m in app.markdown) + "\n" + "\n".join(c.value for c in app.caption)
        for qualification in ("General, News sources and Analysis models", "Saving settings does not fetch",
                              "Selected media", "Latest news only", "NewsData remains manually paused",
                              "Unknown account balance", "not-applicable analysis", "collect-only",
                              "DeepSeek", "not the automatic real-news pipeline",
                              "Repeated-load stability remains unverified", "blocked by resource preflight"):
            self.assertIn(qualification, text)
        about = next(e for e in app.expander if e.label == "About FinScope")
        self.assertTrue(any("3 November 2026 / 7e6c515" in c.value for c in about.caption))
        self.assertTrue(all(not e.proto.expanded for e in app.expander))

    def test_home_capabilities_are_visible_and_scoped_to_the_local_product(self):
        app = self.app()
        self.assertTrue(any(h.value == "Local Product Capabilities" for h in app.subheader))
        cards = next(m.value for m in app.markdown if 'aria-label="Local product capabilities"' in m.value)
        self.assertEqual(cards.count('<article class="fs-product-capability">'), 4)
        for title in ("News collection", "Background processing", "Model selection", "Sector intelligence"):
            self.assertIn('<h3>' + title + '</h3>', cards)
        self.assertIn("Defaults + optional", cards)
        self.assertIn("limited authored-text interface test", cards)
        self.assertFalse(any('aria-label="Local product capabilities"' in m.value
                             for e in app.expander for m in e.markdown))
        self.assertTrue(any("this website does not collect news" in c.value for c in app.caption))
        self.assertEqual(workflow_titles(app), [(1, "Settings"), (2, "Update & Analyze"),
                                               (3, "Background Worker"), (4, "Dashboard")])

    def test_visible_hierarchy_counts_follow_original_dashboard_filters(self):
        app = self.app()
        navigate(app, "Dashboard Preview")
        self.assertTrue(any(h.value == "Industry intelligence" for h in app.subheader))
        self.assertFalse(any(w.key == "preview_topic_parent" for e in app.expander for w in e.selectbox))
        hierarchy = lambda: next(m.value for m in app.markdown
                                 if 'aria-label="Authored parent and child industry hierarchy"' in m.value)
        counts = lambda: [int(n) for n in re.findall(r'data-original-count="(\d+)"', hierarchy())]
        self.assertEqual(sum(counts()), 24)
        self.assertIn('data-topic-parent="Unclassified" data-original-count="17"', hierarchy())
        self.assertIn("Retail operations", hierarchy())
        app.multiselect(key="preview_sectors").set_value(["Technology"]).run()
        self.assertEqual(sum(counts()), 4)
        self.assertIn('data-topic-parent="Unclassified" data-original-count="3"', hierarchy())
        self.assertEqual(app.metric[0].value, "4")
        next(b for b in app.button if b.label == "Reset preview").click().run()
        self.assertEqual(sum(counts()), 24)
        self.assertEqual(app.metric[0].value, "24")

    def test_topic_navigation_inherits_dashboard_selection_and_resets(self):
        app = self.app()
        navigate(app, "Dashboard Preview")
        topic_table = lambda: next(d.value for d in app.dataframe if "Text topic parent" in d.value.columns)
        self.assertEqual(len(topic_table()), 24)
        app.selectbox(key="preview_topic_parent").set_value("Financial services").run()
        self.assertEqual(set(topic_table()["Headline"]), {"Savings Tool Introduced", "Digital Service Expands"})
        app.selectbox(key="preview_topic_child__Financial services").set_value("Savings products").run()
        self.assertEqual(list(topic_table()["Headline"]), ["Savings Tool Introduced"])
        self.assertEqual(app.metric[0].value, "24")
        app.multiselect(key="preview_sectors").set_value(["Technology"]).run()
        self.assertEqual(app.metric[0].value, "4")
        self.assertTrue(any("No authored topic examples" in i.value for i in app.info))
        next(b for b in app.button if b.label == "Reset preview").click().run()
        self.assertEqual(app.selectbox(key="preview_topic_parent").value, "All topic parents")
        self.assertEqual(app.selectbox(key="preview_topic_child__All topic parents").value, "All child topics")
        self.assertEqual(len(topic_table()), 24)
        self.assertEqual(app.metric[0].value, "24")
        app.selectbox(key="preview_topic_parent").set_value("Unclassified").run()
        self.assertEqual(len(topic_table()), 17)
        self.assertTrue(all(topic_table()["Company industry"]))
        self.assertEqual(set(topic_table()["Text topic child"]), {"No child label"})
        self.assertTrue(app.selectbox(key="preview_topic_child__Unclassified").disabled)
        self.assertFalse(app.exception)

    def test_article_topic_context_is_consistent_without_invented_model_history(self):
        app = self.app()
        navigate(app, "Knowledge Graph")
        app.selectbox(key="graph_company").set_value("Harbor Ledger Bank").run()
        article_widget(app, "graph_article").set_value("SYN-010").run()
        expected = "Text topic: Financial services / Savings products · authored illustration"
        self.assertTrue(any(c.value == expected for c in app.caption))
        app.radio(key="graph_cloud_scope").set_value("Selected company").run()
        app.selectbox(key="graph_cloud_word").set_value("savings").run()
        self.assertEqual(article_widget(app, "graph_cloud_article").value, "SYN-010")
        self.assertEqual(sum(c.value == expected for c in app.caption), 2)
        navigate(app, "News Explorer")
        app.text_input[0].set_value("savings").run()
        self.assertEqual(article_widget(app, "explorer_article").value, "SYN-010")
        self.assertTrue(any(c.value == expected for c in app.caption))
        text = "\n".join(m.value for m in app.markdown)
        self.assertIn("Collection cohort: Not applicable", text)
        self.assertIn("Model history: Not applicable", text)
        self.assertFalse(app.exception)

    def test_dashboard_filters_raw_counts_and_reset(self):
        app = self.app()
        navigate(app, "Dashboard Preview")
        self.assertEqual(app.metric[0].value, "24")
        self.assertTrue(any("Demo Data / Illustrative Preview" in m.value for m in app.markdown))
        app.multiselect(key="preview_sectors").set_value(["Technology"]).run()
        self.assertEqual(app.metric[0].value, "4")
        app.multiselect(key="preview_sentiments").set_value(["Positive"]).run()
        self.assertEqual(app.metric[0].value, "2")
        next(b for b in app.button if b.label == "Reset preview").click().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.metric[0].value, "24")
        self.assertEqual(app.multiselect(key="preview_sectors").value, [])
        self.assertEqual(app.multiselect(key="preview_sentiments").value, [])
        self.assertEqual(tuple(app.date_input(key="preview_dates").value), (START, END))

    def test_explorer_and_graph_resolve_only_fictional_records(self):
        app = self.app()
        navigate(app, "News Explorer")
        app.text_input[0].set_value("no such fictional company").run()
        self.assertTrue(any("No fictional examples" in info.value for info in app.info))
        navigate(app, "Knowledge Graph")
        for company in ("Aster Circuits", "Maple Commerce"):
            app.selectbox(key="graph_company").set_value(company).run()
            self.assertFalse(app.exception)
            chosen = article_widget(app, "graph_article").value
            self.assertIn(chosen, {r.article_id for r in examples() if r.company == company})
            self.assertTrue(any("No publisher URL" in c.value for c in app.caption))

    def test_public_entrypoint_and_dependencies_stay_independent(self):
        entrypoint = (ROOT / "deploy/streamlit_app.py").read_text(encoding="utf-8")
        self.assertIn("from finscope.showcase import main", entrypoint)
        self.assertNotIn("from streamlit_app import", entrypoint)
        packages = [line.split(">=")[0] for line in (ROOT / "deploy/requirements.txt").read_text().splitlines()
                    if line.strip() and not line.startswith("#")]
        self.assertEqual(packages, ["streamlit", "pandas"])
        self.assertIn("requirements-finbert.txt", (ROOT / "requirements-local.txt").read_text())


    def test_cloud_drilldown_survives_scope_company_and_network_changes(self):
        app = self.app()
        navigate(app, "Knowledge Graph")
        app.selectbox(key="graph_cloud_word").set_value("research").run()
        self.assertFalse(app.exception)
        table = next(frame.value for frame in app.dataframe if "Article ID" in frame.value.columns)
        expected = next(t["article_ids"] for t in word_cloud_terms(examples()) if t["term"] == "research")
        self.assertEqual(set(table["Article ID"]), set(expected))
        app.radio(key="graph_cloud_scope").set_value("Selected company").run()
        app.selectbox(key="graph_company").set_value("Maple Commerce").run()
        self.assertFalse(app.exception)
        valid = {r.article_id for r in examples() if r.company == "Maple Commerce"}
        self.assertIn(article_widget(app, "graph_cloud_article").value, valid)
        app.radio(key="graph_perspective").set_value("Industry network").run()
        app.checkbox(key="graph_network_sources").set_value(True).run()
        self.assertFalse(app.exception)
        app.radio(key="graph_perspective").set_value("Company focus").run()
        self.assertFalse(app.exception)

    def test_human_article_selection_resolves_stable_id_and_shared_display_label(self):
        rows = [r for r in examples() if r.company == "Cedar Therapeutics"]
        app = self.app()
        navigate(app, "Knowledge Graph")
        self.assertFalse(app.checkbox(key="graph_company_sources").value)
        app.selectbox(key="graph_company").set_value("Cedar Therapeutics").run()
        self.assertEqual(set(article_widget(app, "graph_article").options), {article_label(r) for r in rows})
        article_widget(app, "graph_article").set_value("SYN-007").run()
        chosen = next(r for r in rows if r.article_id == "SYN-007")
        content = "\n".join(m.value for m in app.markdown)
        self.assertIn(article_label(chosen), content)
        self.assertIn(chosen.title, content)
        self.assertIn(chosen.summary, content)
        self.assertTrue(app.expander)
        self.assertTrue(all(not e.proto.expanded for e in app.expander))
        app.selectbox(key="graph_cloud_word").set_value("research").run()
        self.assertNotIn("SYN-", " ".join(article_widget(app, "graph_cloud_article").options))
        article_widget(app, "graph_cloud_article").set_value("SYN-005").run()
        matches = next(d.value for d in app.dataframe if "Complete headline" in d.value.columns)
        self.assertEqual(set(matches["Headline"]), {article_label(r) for r in examples()
                                                  if r.article_id in ("SYN-002", "SYN-005", "SYN-006")})
        navigate(app, "News Explorer")
        app.text_input[0].set_value("Cedar Therapeutics").run()
        listing = app.dataframe[0].value
        self.assertEqual(set(listing["Headline"]), {article_label(r) for r in rows})
        # The compact list retains every headline; inspect each record in its panel.
        for row in rows:
            article_widget(app, "explorer_article").set_value(row.article_id).run()
            content = "\n".join(m.value for m in app.markdown)
            self.assertIn(row.title, content)
            self.assertIn(row.summary, content)
        app.text_input[0].set_value(article_label(chosen)).run()
        self.assertTrue(any(chosen.summary in m.value for m in app.markdown))
        self.assertFalse(any(r.summary in m.value for r in rows if r != chosen for m in app.markdown))
        self.assertFalse(app.exception)

    def test_unrelated_company_reports_do_not_gain_candidate_clutter(self):
        app = self.app()
        navigate(app, "Knowledge Graph")
        for company in ("Harbor Ledger Bank", "Maple Commerce", "Copperleaf Minerals"):
            app.selectbox(key="graph_company").set_value(company).run()
            self.assertEqual(app.metric[1].value, "0")
            self.assertTrue(any("remain separate" in item.value for item in app.info))
            self.assertFalse(app.exception)

    def test_explorer_filters_discard_stale_article_and_keep_all_originals(self):
        app = self.app()
        navigate(app, "News Explorer")
        self.assertEqual(len(app.dataframe[0].value), 24)
        article_widget(app, "explorer_article").set_value("SYN-005").run()
        next(w for w in app.selectbox if w.label == "Example industry").set_value("Technology").run()
        technology = {r.article_id for r in examples() if r.sector == "Technology"}
        self.assertEqual(len(app.dataframe[0].value), 4)
        self.assertIn(article_widget(app, "explorer_article").value, technology)
        app.text_input[0].set_value("no matching authored headline").run()
        self.assertTrue(any("No fictional examples" in item.value for item in app.info))
        app.text_input[0].set_value("").run()
        self.assertIn(article_widget(app, "explorer_article").value, technology)
        self.assertFalse(app.exception)

    def test_clearable_article_picker_has_an_empty_state_and_recovers(self):
        app = self.app()
        for page, key in (("News Explorer", "explorer_article"), ("Knowledge Graph", "graph_article")):
            navigate(app, page)
            article_widget(app, key).set_value(None).run()
            self.assertFalse(app.exception)
            self.assertTrue(any("Select a headline" in item.value for item in app.info))
            article_widget(app, key).set_value("SYN-001").run()
            self.assertFalse(app.exception)
            self.assertTrue(any(examples()[0].summary in item.value for item in app.markdown))


class FictionalDataTests(unittest.TestCase):
    def test_translation_templates_preserve_values_and_preferences_are_isolated(self):
        from concurrent.futures import ThreadPoolExecutor
        from string import Formatter
        from finscope.showcase_preferences import LANGUAGE, APPEARANCE, preferences, t, localize_html
        from finscope.showcase_zh import ZH
        from finscope.showcase_theme import theme_tokens
        for english, chinese in ZH.items():
            fields = lambda text: sorted(name for _, name, _, _ in Formatter().parse(text) if name is not None)
            self.assertEqual(fields(english), fields(chinese), english)
        def render(language, appearance):
            with preferences(language, appearance):
                result = (t("Home"), theme_tokens()["background"])
                self.assertIn('data-topic-parent="Technology"', localize_html(
                    '<h3 data-topic-parent="Technology">Technology</h3>'))
                return result
        with ThreadPoolExecutor(max_workers=2) as pool:
            a = pool.submit(render, "zh-CN", "light")
            b = pool.submit(render, "en", "dark")
            self.assertEqual(a.result(), ("首页", "#f4f7fb"))
            self.assertEqual(b.result(), ("Home", "#0b1220"))
        with self.assertRaises(RuntimeError):
            with preferences("zh-CN", "light"):
                raise RuntimeError("synthetic failure")
        self.assertEqual((LANGUAGE.get(), APPEARANCE.get()), ("en", "dark"))

    def test_both_palettes_cover_graph_cloud_and_normal_text_contrast(self):
        from finscope.showcase_preferences import preferences
        from finscope.showcase_theme import theme_tokens
        from finscope.showcase_visuals import relationship_markup, visible_graph, word_cloud_markup
        def luminance(color):
            channels = [int(color[n:n+2], 16) / 255 for n in (1, 3, 5)]
            linear = [c / 12.92 if c <= .04045 else ((c + .055) / 1.055) ** 2.4 for c in channels]
            return sum(a * b for a, b in zip(linear, (.2126, .7152, .0722)))
        for appearance in ("light", "dark"):
            with preferences("zh-CN", appearance):
                tokens = theme_tokens()
                for foreground in ("text", "muted", "accent", "positive", "neutral", "negative", "industry", "candidate", "source"):
                    for background in ("background", "surface", "raised"):
                        a, b = sorted((luminance(tokens[foreground]), luminance(tokens[background])))
                        self.assertGreaterEqual((b + .05) / (a + .05), 4.5,
                                                (appearance, foreground, background))
                graph_html = relationship_markup(visible_graph(graph(examples(), "Cedar Therapeutics"), False))
                cloud_html = word_cloud_markup(word_cloud_terms(examples()))
                self.assertIn('fill="' + tokens["raised"] + '"', graph_html)
                self.assertIn("未验证的候选关联", graph_html)
                self.assertIn("Research Centre Opens", graph_html)
                # The translation pass must preserve self-closing SVG elements.
                from xml.etree import ElementTree
                svg = ElementTree.fromstring(re.search(r'(<svg .*?</svg>)', graph_html, re.S).group(1))
                self.assertEqual(len(svg.findall('.//{http://www.w3.org/2000/svg}g')), 7)
                self.assertIn("research", cloud_html)
                self.assertIn("background:" + tokens["raised"], cloud_html)

    def test_every_original_headline_frequency_and_match_set_is_unchanged(self):
        # Release baseline across all 24 originals and each of the six companies.
        scopes = {"All fictional headlines": examples(),
                  **{c: [r for r in examples() if r.company == c]
                     for c in sorted({r.company for r in examples()})}}
        data = {name: word_cloud_terms(rows, limit=10000) for name, rows in scopes.items()}
        digest = hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()
        self.assertEqual(digest, "84745a5e524f2a4ae0b0429aa3727e0193dbd11b130a29b00dc9add0617afcb4")

    def test_authored_topic_evidence_and_unclassified_do_not_infer_company_industry(self):
        from finscope.showcase_content import AUTHORED_TOPICS, topic_context, topic_select
        rows = examples()
        self.assertLessEqual(set(AUTHORED_TOPICS), {r.article_id for r in rows})
        for row in rows:
            info = topic_context(row)
            if info["evidence"]:
                self.assertIn(info["evidence"], (row.title + " " + row.summary).casefold())
                self.assertEqual(info["status"], "Authored illustration")
            else:
                self.assertEqual(info["parent"], "Unclassified")
                self.assertIsNone(info["child"])
        logistics = next(r for r in rows if r.article_id == "SYN-023")
        self.assertEqual(logistics.sector, "Consumer")
        self.assertEqual(topic_context(logistics)["parent"], "Industrials")
        self.assertEqual({r.article_id for r in topic_select(rows, "Consumer", "Retail operations")},
                         {"SYN-021", "SYN-022"})
        self.assertTrue(all(r.company == "Cedar Therapeutics" for r in rows[4:8]))
        self.assertTrue(all(topic_context(r)["parent"] == "Unclassified" for r in rows[4:8]))

    def test_landing_preview_uses_real_fixture_counts_and_filtered_input(self):
        from finscope.showcase_theme import dashboard_preview
        full = dashboard_preview(examples())
        self.assertIn('data-report-count="24"', full)
        self.assertIn('data-positive-count="11"', full)
        self.assertIn('Technology: 2 Positive, 1 Neutral, 1 Negative', full)
        one = dashboard_preview([examples()[0]])
        self.assertIn('data-report-count="1"', one)
        self.assertIn('data-positive-count="1"', one)
        self.assertIn('100%', one)
        self.assertNotIn('data-report-count="24"', one)

    def test_public_text_tokens_meet_normal_text_contrast(self):
        from finscope.showcase_theme import TOKENS

        def luminance(color):
            channels = [int(color[n:n+2], 16) / 255 for n in (1, 3, 5)]
            linear = [c / 12.92 if c <= .04045 else ((c + .055) / 1.055) ** 2.4 for c in channels]
            return sum(a * b for a, b in zip(linear, (.2126, .7152, .0722)))

        for foreground in ("text", "muted", "accent", "positive", "neutral", "negative", "industry"):
            for background in ("background", "surface", "raised"):
                a, b = sorted((luminance(TOKENS[foreground]), luminance(TOKENS[background])))
                self.assertGreaterEqual((b + .05) / (a + .05), 4.5, (foreground, background))
        a, b = sorted((luminance(TOKENS["text"]), luminance(TOKENS["button"])))
        self.assertGreaterEqual((b + .05) / (a + .05), 4.5)

    def test_responsive_graph_layout_retains_all_evidence_without_node_collisions(self):
        from finscope.showcase_visuals import graph_layout, visible_graph
        rows = examples()
        for company in {r.company for r in rows}:
            for sources in (True, False):
                data = visible_graph(graph(rows, company), sources)
                width, height, positions, sizes = graph_layout(data)
                self.assertEqual(set(positions), {n["id"] for n in data["nodes"]})
                boxes = []
                for ident, (x, y) in positions.items():
                    w, h = sizes[ident]
                    box = (x - w/2, y - h/2, x + w/2, y + h/2)
                    self.assertTrue(0 <= box[0] < box[2] <= width, ident)
                    self.assertTrue(0 <= box[1] < box[3] <= height, ident)
                    for other in boxes:
                        self.assertFalse(min(box[2], other[2]) > max(box[0], other[0])
                                         and min(box[3], other[3]) > max(box[1], other[1]))
                    boxes.append(box)

    def test_readable_labels_and_complete_tooltips_never_expose_technical_codes(self):
        from html.parser import HTMLParser
        from finscope.showcase_visuals import relationship_markup, visible_graph

        class SvgText(HTMLParser):
            def __init__(self):
                super().__init__()
                self.tag = ""
                self.words = []

            def handle_starttag(self, tag, attrs):
                self.tag = tag

            def handle_data(self, data):
                if self.tag in ("text", "title"):
                    self.words.append(data)

            def handle_endtag(self, tag):
                self.tag = ""

        rows = examples()
        self.assertEqual([r.article_id for r in rows], [f"SYN-{n:03}" for n in range(1, 25)])
        self.assertEqual(len({article_label(r) for r in rows}), 24)
        self.assertTrue(all(8 < len(article_label(r)) <= 32 for r in rows))
        for company in {r.company for r in rows}:
            data = graph(rows, company)
            self.assertEqual(len({n["id"] for n in data["nodes"]}), len(data["nodes"]))
            parsed = SvgText()
            parsed.feed(relationship_markup(visible_graph(data, False)))
            self.assertNotRegex(" ".join(parsed.words), r"\b(?:SYN-\d+|C-\d+-\d+)\b")
            for row in (r for r in rows if r.company == company):
                node = next(n for n in data["nodes"] if n["id"] == row.article_id)
                self.assertEqual(node["label"], article_label(row))
                tooltip = next(w for w in parsed.words if row.title in w and row.summary in w)
                for field in (row.company, row.sector, row.sentiment, row.day.isoformat(), row.source):
                    self.assertIn(field, tooltip)
                self.assertIn(row.sentiment + " sentiment", parsed.words)

    def test_reviewed_candidate_topics_and_singleton_suppression(self):
        rows = examples()
        expected = {"C-1-0": {"SYN-001", "SYN-002"},
                    "C-2-0": {"SYN-005", "SYN-006"},
                    "C-4-0": {"SYN-013", "SYN-014"}}
        groups = candidate_groups(rows)
        self.assertEqual({g["id"]: set(g["article_ids"]) for g in groups}, expected)
        self.assertTrue(all(g["label"] and g["basis"] and len(g["article_ids"]) > 1 for g in groups))
        self.assertTrue(all(not r.candidate for r in rows if r.article_id in
                            ("SYN-009", "SYN-010", "SYN-021", "SYN-022")))
        for company in {r.company for r in rows}:
            data = graph(rows, company)
            for node in (n for n in data["nodes"] if n["kind"] == "Unverified candidate"):
                self.assertEqual(set(node["article_ids"]), expected[node["id"]])
                self.assertGreater(len([e for e in data["edges"] if e["to_id"] == node["id"]]), 1)
        self.assertFalse(candidate_groups([rows[0]]))
        self.assertFalse(any(n["kind"] == "Unverified candidate" for n in graph([rows[0]], rows[0].company)["nodes"]))
        research = next(t for t in word_cloud_terms(rows) if t["term"] == "research")
        self.assertEqual(research, {"term": "research", "count": 3,
                                    "article_ids": ("SYN-002", "SYN-005", "SYN-006")})

    def test_article_node_context_and_both_edge_schemas_are_preserved(self):
        records = examples()
        self.assertEqual(len({row.summary for row in records}), len(records))
        by_id = {row.article_id: row for row in records}
        for node in graph(records, "Aster Circuits")["nodes"]:
            if node["kind"] == "Article":
                row = by_id[node["article_id"]]
                self.assertEqual((node["title"], node["summary"], node["sentiment"], node["source"],
                                  node["company"], node["industry"], node["candidate"]),
                                 (row.title, row.summary, row.sentiment, row.source,
                                  row.company, row.sector, row.candidate))
        for data in (graph(records, "Aster Circuits"), graph_overview(records)):
            for edge in data["edges"]:
                self.assertEqual((edge["from"], edge["to"]), (edge["from_id"], edge["to_id"]))

    def test_source_visibility_keeps_article_and_candidate_relationships(self):
        from finscope.showcase_visuals import visible_graph
        original = graph(examples(), "Aster Circuits")
        reduced = visible_graph(original, False)
        self.assertFalse(any(n["kind"] == "Source" for n in reduced["nodes"]))
        self.assertEqual({n["id"] for n in reduced["nodes"] if n["kind"] == "Article"},
                         {n["id"] for n in original["nodes"] if n["kind"] == "Article"})
        ids = {n["id"] for n in reduced["nodes"]}
        self.assertTrue(all(e["from_id"] in ids and e["to_id"] in ids for e in reduced["edges"]))
        self.assertTrue(any("candidate" in e["relationship"].lower() for e in reduced["edges"]))
        self.assertEqual(visible_graph(original), original)

    def test_headline_frequency_is_document_frequency_with_exact_evidence(self):
        from dataclasses import replace
        rows = [replace(examples()[0], title="Research research: company news update"),
                replace(examples()[1], title="Research expands")]
        terms = {t["term"]: t for t in word_cloud_terms(rows)}
        self.assertEqual(terms["research"]["count"], 2)
        self.assertEqual(set(terms["research"]["article_ids"]), {r.article_id for r in rows})
        self.assertFalse({"company", "news", "update"} & set(terms))

    def test_fixture_identity_no_urls_and_filter_denominators(self):
        rows = examples()
        self.assertEqual(len({r.article_id for r in rows}), 24)
        self.assertTrue(all(r.synthetic and not hasattr(r, "url") for r in rows))
        selected = select(rows, START, END, ["Technology"], ["Positive"])
        self.assertEqual(len(selected), 2)
        self.assertEqual(select(rows, END, START), [])
        self.assertEqual(select(rows, START, END, search="nonexistent"), [])
        self.assertTrue(all(START <= r.day <= END for r in rows))

    def test_graph_edges_resolve_fictional_entities_and_keep_articles(self):
        rows = examples()
        data = graph(rows, "Aster Circuits")
        ids = {n["id"] for n in data["nodes"]}
        self.assertEqual({n["kind"] for n in data["nodes"]},
                         {"Company", "Industry", "Article", "Source", "Unverified candidate"})
        for edge in data["edges"]:
            self.assertIn(edge["from"], ids)
            self.assertIn(edge["to"], ids)
            self.assertIn(edge["article_id"], {r.article_id for r in rows})
        self.assertEqual(graph(rows, "Nonexistent"), {"nodes": [], "edges": []})


    def test_industry_network_aggregates_only_fixture_evidence(self):
        rows = examples()
        network = graph_overview(rows)
        self.assertEqual(len([n for n in network["nodes"] if n["kind"] == "Company"]), 6)
        self.assertEqual(len([n for n in network["nodes"] if n["kind"] == "Industry"]), 6)
        self.assertEqual(len([n for n in network["nodes"] if n["kind"] == "Source"]), 3)
        ids = {n["id"] for n in network["nodes"]}
        self.assertTrue(network["edges"])
        self.assertTrue(all(e["from_id"] in ids and e["to_id"] in ids
                            and e["count"] >= 1 for e in network["edges"]))
        source_edges = [e for e in network["edges"]
                        if e["relationship"] == "Fictional source reports on company"]
        self.assertEqual(sum(e["count"] for e in source_edges), 24)
        self.assertEqual(graph_overview([]), {"nodes": [], "edges": []})

    def test_word_cloud_counts_fixture_titles_not_filler_text(self):
        records = examples()
        terms = word_cloud_terms(records)
        self.assertTrue(terms)
        self.assertLessEqual(len(terms), 16)
        self.assertEqual(terms, word_cloud_terms(records))
        self.assertNotIn("fictional", {item["term"] for item in terms})
        self.assertNotIn("aster", {item["term"] for item in terms})
        self.assertTrue(all(item["count"] == len(item["article_ids"]) for item in terms))
        self.assertTrue(all(set(item["article_ids"]) <= {r.article_id for r in records}
                            for item in terms))
        self.assertEqual(word_cloud_terms(records, limit=0), [])
        company_rows = [r for r in records if r.company == "Aster Circuits"]
        small = word_cloud_terms(company_rows)
        self.assertTrue(small)
        self.assertTrue(all(item["count"] <= 4 for item in small))
        self.assertEqual(word_cloud_terms([], limit=16), [])

    def test_graph_word_cloud_and_perspective_controls_render(self):
        # This method runs as a data test but exercises the public AppTest entrypoint.
        app = AppTest.from_file(str(ROOT / "deploy/streamlit_app.py"), default_timeout=15).run()
        navigate(app, "Knowledge Graph")
        self.assertFalse(app.exception)
        self.assertTrue(any("Headline word cloud" in h.value for h in app.subheader))
        app.radio(key="graph_perspective").set_value("Industry network").run()
        self.assertFalse(app.exception)
        app.radio(key="graph_cloud_scope").set_value("Selected company").run()
        self.assertFalse(app.exception)
        self.assertTrue(any("authored fictional headlines" in c.value for c in app.caption))
