"""Test de fumée de l'application : Streamlit et Plotly sont remplacés par des doublons.

Il vérifie que chaque onglet s'exécute de bout en bout avec les vraies données du pipeline
(noms de colonnes, indicateurs, rôles) sans lancer de serveur.
"""

import importlib
import sys
import unittest
from unittest.mock import MagicMock, patch


def fake_streamlit(session):
    st = MagicMock()
    st.session_state = session
    st.cache_data = lambda function: function
    st.tabs.side_effect = lambda names: [MagicMock() for _ in names]
    st.columns.side_effect = lambda n: [MagicMock() for _ in range(n)]
    st.selectbox.return_value = "Tous"
    st.sidebar.button.return_value = False
    return st


class TestAppSmoke(unittest.TestCase):
    def run_app(self, session):
        st = fake_streamlit(session)
        plotly = MagicMock()
        modules = {"streamlit": st, "plotly": plotly, "plotly.express": plotly.express}
        with patch.dict(sys.modules, modules):
            sys.modules.pop("streamlit_app", None)
            app = importlib.import_module("streamlit_app")
            app.main()
            sys.modules.pop("streamlit_app", None)
        return st, plotly.express

    def test_login_page_when_not_connected(self):
        st, _ = self.run_app({})
        st.form_submit_button.assert_called_once()
        st.tabs.assert_not_called()

    def test_admin_sees_six_tabs_and_quality_report(self):
        st, px = self.run_app({"role": "admin", "username": "admin"})
        self.assertEqual(len(st.tabs.call_args.args[0]), 6)
        st.download_button.assert_called_once()
        self.assertGreaterEqual(px.bar.call_count, 8)
        px.imshow.assert_called_once()

    def test_user_sees_five_tabs_and_masked_duplicates(self):
        st, _ = self.run_app({"role": "user", "username": "user"})
        self.assertEqual(len(st.tabs.call_args.args[0]), 5)
        st.download_button.assert_not_called()
        shown = st.dataframe.call_args_list[-1].args[0]
        self.assertTrue(shown["name_a"].str.contains(r"\*\*\*").all())


if __name__ == "__main__":
    unittest.main()
