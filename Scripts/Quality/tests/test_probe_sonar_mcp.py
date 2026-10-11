import importlib.util
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "probe_sonar_mcp.py"
SPEC = importlib.util.spec_from_file_location("probe_sonar_mcp", SCRIPT)
assert SPEC and SPEC.loader
probe = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(probe)


class McpProbeArgumentTests(unittest.TestCase):
    def test_probe_container_name_is_private_and_unique_shaped(self):
        name = probe.new_probe_container_name()
        self.assertRegex(name, r"^quality-mcp-probe-[0-9a-f]{16}$")
        self.assertNotEqual(name, probe.new_probe_container_name())

    def test_cleanup_command_targets_only_generated_probe_name(self):
        name = "quality-mcp-probe-0123456789abcdef"
        self.assertEqual(
            probe.probe_container_cleanup_command("docker", name),
            ["docker", "container", "rm", "--force", name],
        )
        with self.assertRaisesRegex(probe.ProbeError, "Refusing cleanup"):
            probe.probe_container_cleanup_command("docker", "sonarqube")

    def test_issue_call_uses_only_advertised_project_and_paging_fields(self):
        schema = {"properties": {"projectKeys": {"type": "array"}, "pageSize": {"type": "integer"}}}
        self.assertEqual(
            probe.build_tool_arguments("search_sonar_issues_in_projects", schema, "repo-BlazorAuto"),
            {"projectKeys": ["repo-BlazorAuto"], "pageSize": 1},
        )

    def test_project_default_removes_project_key_from_measures_schema(self):
        schema = {"properties": {"metricKeys": {"type": "array"}}}
        self.assertEqual(
            probe.build_tool_arguments("get_component_measures", schema, "repo-React"),
            {"metricKeys": ["ncloc", "coverage"]},
        )

    def test_required_unknown_argument_fails_closed(self):
        with self.assertRaisesRegex(probe.ProbeError, "lack probe values"):
            probe.build_tool_arguments("show_rule", {"properties": {}, "required": ["language"]}, "repo")

    def test_read_only_tool_contract_names(self):
        self.assertTrue(probe.REQUIRED_TOOLS.issubset({
            "search_sonar_issues_in_projects",
            "show_rule",
            "get_component_measures",
            "search_files_by_coverage",
            "get_project_quality_gate_status",
        }))
        self.assertIn("change_sonar_issue_status", probe.FORBIDDEN_TOOLS)
        self.assertIn("change_security_hotspot_status", probe.FORBIDDEN_TOOLS)


if __name__ == "__main__":
    unittest.main()
