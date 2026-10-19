"""Unit tests for value resolution, the condition model, output parsing and loading.

Examples are taken from the Dagu specs (003/005/007, 023, 012) so the runner's reading
of the syntax matches theirs.
"""

import textwrap

import pytest

from runner.conditions import Condition, EvalError
from runner.outputs import OutputError, parse_output_file
from runner.resolve import Scope, resolve, step_refs
from runner.spec import SpecError, load, normalize, resolve_params, validate_schema

SH = ["sh", "-c"]


def write(tmp_path, text, name="wf.yaml"):
    p = tmp_path / name
    p.write_text(textwrap.dedent(text))
    return str(p)


# ----- resolve -----------------------------------------------------------------


def test_resolve_supported_references_and_preserve_the_rest():
    scope = Scope(params={"unit": "1.3a"}, env={"HOME": "/h"}, steps={"build": {"image": "v1"}})
    text = "u=${params.unit} h=${env.HOME} i=${steps.build.outputs.image} $NAME ${NAME} $(date) ${steps.x.outputs.y}"
    assert resolve(text, scope) == "u=1.3a h=/h i=v1 $NAME ${NAME} $(date) ${steps.x.outputs.y}"


def test_escaped_reference_is_literal_text():
    scope = Scope(params={"a": "1"})
    assert resolve(r"\${params.a} ${params.a}", scope) == "${params.a} 1"
    assert step_refs(r"\${steps.b.outputs.y} ${steps.a.outputs.x}") == [("a", "x")]


def test_params_payload_is_json():
    assert resolve("${params}", Scope(params={"b": "2", "a": "1"})) == '{"a": "1", "b": "2"}'


# ----- conditions ---------------------------------------------------------------


def test_literal_match_is_per_line_and_case_sensitive():
    scope = Scope(params={"v": "staging\nproduction"})
    assert Condition("${params.v}", "production").check(scope, {}, None, SH)
    assert not Condition("${params.v}", "Production").check(scope, {}, None, SH)


def test_regex_match_from_spec_example():
    c = Condition("${params.environment}", "re:^(staging|production)$")
    assert c.check(Scope(params={"environment": "staging"}), {}, None, SH)
    assert not c.check(Scope(params={"environment": "dev"}), {}, None, SH)


def test_numeric_match_with_reference_threshold_and_errors():
    scope = Scope(params={"score": "0.85", "threshold": "0.8"}, steps={"r": {"findings": "2"}})
    assert Condition("${params.score}", "num:>=${params.threshold}").check(scope, {}, None, SH)
    assert Condition("${steps.r.outputs.findings}", "num:>0").check(scope, {}, None, SH)
    assert not Condition("${steps.r.outputs.findings}", "num:> 5").check(scope, {}, None, SH)
    with pytest.raises(EvalError):  # a non-number is an evaluation error, not "not met"
        Condition("${params.environment}", "num:>0").check(scope, {}, None, SH)
    with pytest.raises(ValueError):
        Condition("x", "num:==1").validate()
    with pytest.raises(ValueError):
        Condition("x", "num:>=0.${threshold}").validate()


def test_negate_inverts_only_normal_results():
    scope = Scope(params={"env": "production"})
    assert not Condition("${params.env}", "production", negate=True).check(scope, {}, None, SH)
    assert Condition("${params.env}", "dev", negate=True).check(scope, {}, None, SH)
    with pytest.raises(EvalError):
        Condition("${params.env}", "num:>1", negate=True).check(scope, {}, None, SH)


def test_command_check_uses_exit_code(tmp_path):
    flag = tmp_path / "ready.flag"
    c = Condition(f"test -f {flag}")
    assert not c.check(Scope(), {}, None, SH)
    flag.write_text("")
    assert c.check(Scope(), {}, None, SH)
    assert not Condition("/definitely/missing/binary").check(Scope(), {}, None, SH)


# ----- outputs ------------------------------------------------------------------


def test_output_file_single_and_multiline_records(tmp_path):
    f = tmp_path / "out"
    f.write_text('region=us-east-1\nreplicas=3\nmetadata<<JSON\n{"image":"api","tag":"v1.2.3"}\nJSON\nempty=\n')
    got = parse_output_file(str(f), {"region": "string", "replicas": "string", "metadata": "json", "empty": "string"})
    assert got == {"region": "us-east-1", "replicas": "3", "metadata": '{"image":"api","tag":"v1.2.3"}', "empty": ""}


@pytest.mark.parametrize(
    "content,declared,msg",
    [
        ("image=v1\n", {}, "undeclared"),
        ("", {"image": "string"}, "not emitted"),
        ("image=v1\nimage=v2\n", {"image": "string"}, "more than once"),
        ("m<<EOF\n{\nEOF\n", {"m": "json"}, "not valid JSON"),
        ("m<<EOF\nabc\n", {"m": "string"}, "unclosed"),
        ("a=1\n\nb=2\n", {"a": "string", "b": "string"}, "empty line"),
    ],
)
def test_output_file_errors(tmp_path, content, declared, msg):
    f = tmp_path / "out"
    f.write_text(content)
    with pytest.raises(OutputError, match=msg):
        parse_output_file(str(f), declared)


# ----- spec ---------------------------------------------------------------------


def test_schema_rejects_fields_outside_the_subset():
    with pytest.raises(SpecError, match="action"):
        validate_schema({"steps": [{"id": "a", "action": "router.route", "with": {}}]})
    with pytest.raises(SpecError, match="repeat"):
        validate_schema({"steps": [{"id": "a", "run": "x", "repeat_policy": {"repeat": True}}]})
    with pytest.raises(SpecError, match="human"):
        validate_schema({"steps": [{"id": "a", "run": "x"}], "handler_on": {"wait": {"run": "x"}, "human": 1}})


def test_inferred_dependency_from_spec_007(tmp_path):
    dag = load(write(tmp_path, """
        steps:
          - id: build
            run: printf 'image=v1.2.3\\n' >> "$DAGU_OUTPUT_FILE"
            outputs:
              - name: image
          - id: deploy
            run: echo ${steps.build.outputs.image}
        """))
    assert dag.step("deploy").inferred == ["build"]
    assert dag.step("deploy").all_depends == ["build"]


def test_inferred_dependency_cycle_is_a_load_error(tmp_path):
    with pytest.raises(SpecError, match="cycle"):
        load(write(tmp_path, """
            steps:
              - id: a
                run: echo ${steps.b.outputs.y}
                outputs: [{name: x}]
              - id: b
                run: echo ${steps.a.outputs.x}
                outputs: [{name: y}]
            """))


def test_duplicate_ids_and_unknown_depends(tmp_path):
    with pytest.raises(SpecError, match="duplicate"):
        load(write(tmp_path, "steps:\n  - {id: a, run: x}\n  - {id: a, run: y}\n"))
    with pytest.raises(SpecError, match="unknown step"):
        load(write(tmp_path, "steps:\n  - {id: a, run: x, depends: zz}\n"))


def test_params_defaults_required_and_types():
    dag = normalize(
        {
            "params": [
                {"name": "unit", "required": True},
                {"name": "effort", "default": "medium", "enum": ["low", "medium", "high"]},
                {"name": "rounds", "type": "integer", "default": 2},
            ],
            "steps": [{"id": "a", "run": "x"}],
        },
        "wf.yaml",
    )
    assert resolve_params(dag, {"unit": "1.3a"}) == {"unit": "1.3a", "effort": "medium", "rounds": "2"}
    with pytest.raises(SpecError, match="required"):
        resolve_params(dag, {})
    with pytest.raises(SpecError, match="one of"):
        resolve_params(dag, {"unit": "x", "effort": "max"})
    with pytest.raises(SpecError, match="integer"):
        resolve_params(dag, {"unit": "x", "rounds": "two"})
    with pytest.raises(SpecError, match="unknown param"):
        resolve_params(dag, {"unit": "x", "model": "y"})
