"""Rendu des modules Ansible depuis le modèle intermédiaire.

Le renderer n'a qu'une responsabilité : **écrire**. Toute décision est déjà
prise dans `generator/ansible/models.py`, et le template ne contient aucun test
autre qu'une présence de valeur.

Deux propriétés sont tenues ici et vérifiées par un test :

* **le rendu est déterministe.** Les littéraux Python et les blocs YAML sont
  produits par ce fichier, pas par `repr()` ni par un `json.dumps` dont l'ordre
  dépendrait d'un dictionnaire ;
* **rien n'est rendu que le modèle n'ait décidé.** Si le rendu avait besoin de
  savoir quelque chose que le modèle ne porte pas, c'est le modèle qu'il faut
  compléter.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from jinja2 import Environment, FileSystemLoader, StrictUndefined

from generator.ansible.models import AnsibleModuleSpec, OperationBinding
from generator.ir.enums import OperationKind

TEMPLATE_ROOT = Path(__file__).resolve().parents[1] / "templates"
MODULE_TEMPLATE = "module.py.j2"

#: Largeur de repli des blocs YAML. Les descriptions du contrat sont longues ;
#: au-delà, le fichier produit dépasserait la longueur de ligne du dépôt.
YAML_WIDTH = 88

#: Marque qu'un fichier est produit par le générateur. Un fichier généré édité
#: à la main est effacé à la prochaine génération, et `mise run check:generated`
#: le dit avant que quelqu'un le découvre.
GENERATED_HEADER = "# This file is generated.\n# Do not edit manually."


class RenderError(ValueError):
    """Le modèle ne peut pas être rendu tel quel."""


def render_module(spec: AnsibleModuleSpec, *, source: str) -> str:
    """Rend le fichier d'un module, prêt à être écrit sur disque."""
    template = _environment().get_template(MODULE_TEMPLATE)
    operations = [
        operation.id
        for operation in (spec.get_operation, spec.list_operation, spec.action_operation)
        if operation is not None
    ]

    rendered = template.render(
        generated_header=GENERATED_HEADER,
        authors=", ".join(spec.collection.authors) or spec.collection.fqcn,
        source=source,
        operations=", ".join(operations),
        documentation=_yaml_block(spec.documentation()),
        examples=_yaml_block(spec.examples_documentation()),
        returns=_yaml_block(spec.return_documentation()),
        module_utils_import=spec.collection.module_utils_import,
        runtime_imports=_runtime_imports(spec),
        common_argument_specs=_common_argument_specs(spec),
        argument_spec=python_literal(spec.argument_spec()),
        module_literal=_module_literal(spec),
        run_call=_run_call(spec),
    )
    if not rendered.endswith("\n"):
        rendered += "\n"
    return rendered


def write_modules(
    specs: tuple[AnsibleModuleSpec, ...],
    output_dir: Path,
    *,
    source: str,
) -> list[Path]:
    """Écrit les modules, et rend les chemins produits, triés."""
    output_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for spec in sorted(specs, key=lambda item: item.name):
        target = output_dir / f"{spec.name}.py"
        target.write_text(render_module(spec, source=source), encoding="utf-8")
        written.append(target)
    return written


#: Ce que chaque classe de module exécute. Le renderer choisit, pas le template.
_RUN_FUNCTIONS: dict[OperationKind, str] = {
    OperationKind.INFO: "run_info_module",
    OperationKind.ACTION: "run_action_module",
}

#: La dataclasse de description que chaque classe déclare.
_SPEC_CLASSES: dict[OperationKind, str] = {
    OperationKind.INFO: "InfoModule",
    OperationKind.ACTION: "ActionModule",
}


def _runtime_imports(spec: AnsibleModuleSpec) -> list[str]:
    """Les noms importés du runtime, triés, et aucun de plus.

    Un import inutilisé dans un fichier généré est du bruit qu'un linter
    signalera un jour à quelqu'un qui n'a rien écrit.
    """
    noms = {
        "Operation",
        _SPEC_CLASSES[spec.kind],
        _RUN_FUNCTIONS[spec.kind],
        "scaleway_argument_spec",
    }
    if spec.waitable:
        noms.add("scaleway_waitable_argument_spec")
    return sorted(noms)


def _common_argument_specs(spec: AnsibleModuleSpec) -> list[str]:
    """Les jeux de paramètres communs que le module assemble, dans l'ordre."""
    appels = ["scaleway_argument_spec()"]
    if spec.waitable:
        appels.append("scaleway_waitable_argument_spec()")
    return appels


def _run_call(spec: AnsibleModuleSpec) -> str:
    return f"{_RUN_FUNCTIONS[spec.kind]}(module, MODULE)"


def _module_literal(spec: AnsibleModuleSpec) -> str:
    """Rend la déclaration que le module généré porte, selon sa classe."""
    if spec.kind is OperationKind.ACTION:
        return _action_module_literal(spec)
    return _info_module_literal(spec)


def _action_module_literal(spec: AnsibleModuleSpec) -> str:
    """Rend l'appel `ActionModule(...)`."""
    if spec.action_operation is None or spec.action_parameter is None:
        raise RenderError(f"{spec.name} : module d'action sans opération à déclencher")

    lines = ["ActionModule("]
    lines.append(f"    operation={_operation_literal(spec.action_operation, indent=4)},")
    lines.append(f"    action_parameter={quote(spec.action_parameter)},")
    if spec.read_operation is not None:
        lines.append(f"    read_operation={_operation_literal(spec.read_operation, indent=4)},")
    if spec.wait_states:
        lines.append(f"    state_field={quote(spec.state_field)},")
        etats = dict(spec.wait_states)
        lines.append(f"    wait_states={python_literal(etats, indent=4)},")
    lines.append(")")
    return "\n".join(lines)


def _environment() -> Environment:
    """Environnement Jinja2 du projet.

    `StrictUndefined` est délibéré : une variable de template mal orthographiée
    doit faire échouer la génération, pas produire un trou silencieux dans un
    module.
    """
    return Environment(
        loader=FileSystemLoader(str(TEMPLATE_ROOT)),
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
        # CodeQL signale `py/jinja2/autoescape-false` en gravité haute, et il a
        # raison de le signaler : la règle vise le rendu de HTML, où ne pas
        # échapper ouvre une injection. Ici la sortie est du **code Python**.
        # Échapper y serait le défaut : `&` deviendrait `&amp;` et un guillemet
        # une entité, dans un fichier que l'interpréteur doit lire. Les valeurs
        # rendues ne viennent d'ailleurs pas d'un utilisateur mais d'un contrat
        # OpenAPI versionné, relu en revue avant d'entrer dans le dépôt.
        autoescape=False,  # codeql[py/jinja2/autoescape-false]
    )


def _yaml_block(payload: Any) -> str:
    """Sérialise un bloc de documentation en YAML, sans réordonner les clés.

    L'ordre vient du modèle : il est celui d'une lecture humaine, et le trier
    alphabétiquement mettrait `author` avant `description`.
    """
    text = yaml.safe_dump(
        payload,
        sort_keys=False,
        default_flow_style=False,
        allow_unicode=True,
        width=YAML_WIDTH,
    )
    if '"""' in text:
        raise RenderError("un bloc de documentation contient une triple quote")
    return text.rstrip("\n")


#: Longueur au-delà de laquelle un littéral passe à la ligne. En dessous de la
#: limite du dépôt (100), pour laisser la place à la clé qui le précède.
INLINE_BUDGET = 88


def python_literal(value: Any, *, indent: int = 0) -> str:
    """Rend une valeur Python en littéral déterministe et relisible.

    `repr()` ne convient pas : il écrit des guillemets simples, là où le style
    du dépôt et `ruff format` en attendent des doubles.

    Une collection de valeurs simples reste sur une ligne quand elle y tient.
    Ce n'est pas une décision sur le contenu, c'est de la mise en forme, et
    elle est totale : même entrée, même sortie, octet pour octet.
    """
    pad = " " * indent
    inner = " " * (indent + 4)

    if isinstance(value, dict):
        if not value:
            return "{}"
        inline = _inline_literal(value)
        if inline is not None and indent + len(inline) <= INLINE_BUDGET:
            return inline
        lines = ["{"]
        for key, item in value.items():
            lines.append(f"{inner}{quote(str(key))}: {python_literal(item, indent=indent + 4)},")
        lines.append(pad + "}")
        return "\n".join(lines)

    if isinstance(value, (list, tuple)):
        opening, closing = ("[", "]") if isinstance(value, list) else ("(", ")")
        if not value:
            return f"{opening}{closing}"
        inline = _inline_literal(value)
        if inline is not None and indent + len(inline) <= INLINE_BUDGET:
            return inline
        lines = [opening]
        for item in value:
            lines.append(f"{inner}{python_literal(item, indent=indent + 4)},")
        lines.append(pad + closing)
        return "\n".join(lines)

    return _scalar_literal(value)


def _scalar_literal(value: Any) -> str:
    if isinstance(value, bool) or value is None:
        return str(value)
    if isinstance(value, (int, float)):
        return str(value)
    return quote(str(value))


def _inline_literal(value: Any) -> str | None:
    """Forme sur une ligne d'une collection de scalaires, ou `None`.

    `None` dès qu'un élément n'est pas un scalaire : une structure imbriquée se
    lit mieux dépliée, et la mise en forme ne doit pas dépendre de sa longueur.
    """
    if isinstance(value, dict):
        if not all(_is_scalar(item) for item in value.values()):
            return None
        body = ", ".join(
            f"{quote(str(key))}: {_scalar_literal(item)}" for key, item in value.items()
        )
        return "{" + body + "}"

    if not all(_is_scalar(item) for item in value):
        return None
    body = ", ".join(_scalar_literal(item) for item in value)
    if isinstance(value, tuple) and len(value) == 1:
        # Un tuple d'un seul élément garde sa virgule, sinon ce sont des
        # parenthèses autour d'une valeur.
        return f"({body},)"
    opening, closing = ("[", "]") if isinstance(value, list) else ("(", ")")
    return f"{opening}{body}{closing}"


def _is_scalar(value: Any) -> bool:
    return value is None or isinstance(value, (str, int, float, bool))


def quote(text: str) -> str:
    """Met une chaîne entre guillemets, à la manière de `ruff format`.

    Guillemets doubles par défaut, simples quand cela évite des échappements.
    """
    if '"' in text and "'" not in text:
        return "'" + text.replace("\\", "\\\\") + "'"
    escaped = text.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _info_module_literal(spec: AnsibleModuleSpec) -> str:
    """Rend l'appel `InfoModule(...)` que le module généré déclare."""
    if spec.get_operation is None and spec.list_operation is None:
        raise RenderError(f"{spec.name} : aucune opération à déclarer")

    lines = ["InfoModule("]
    if spec.get_operation is not None:
        lines.append(f"    get_operation={_operation_literal(spec.get_operation, indent=4)},")
    if spec.list_operation is not None:
        lines.append(f"    list_operation={_operation_literal(spec.list_operation, indent=4)},")
    if spec.selector is not None:
        lines.append(f"    selector={quote(spec.selector)},")
    lines.append(")")
    return "\n".join(lines)


def _operation_literal(operation: OperationBinding, *, indent: int) -> str:
    """Rend un appel `Operation(...)`, champs par défaut omis.

    Omettre un champ égal à son défaut n'est pas une décision : c'est le même
    objet, écrit court. Le runtime porte les valeurs par défaut, une seule fois.
    """
    pad = " " * indent
    inner = " " * (indent + 4)

    fields: list[tuple[str, Any]] = [
        ("id", operation.id),
        ("method", operation.method),
        ("path", operation.path),
        ("path_params", operation.path_params),
        ("query_params", operation.query_params),
    ]
    if operation.body_params:
        fields.append(("body_params", operation.body_params))
    if operation.payload_field is not None:
        fields.append(("payload_field", operation.payload_field))
    if operation.is_list:
        fields.append(("is_list", True))
    if operation.page_param is not None:
        fields.append(("page_param", operation.page_param))
    if operation.per_page_param is not None:
        fields.append(("per_page_param", operation.per_page_param))

    lines = ["Operation("]
    for name, value in fields:
        lines.append(f"{inner}{name}={python_literal(value, indent=indent + 4)},")
    lines.append(pad + ")")
    return "\n".join(lines)
