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
from generator.ansible.retry import RetryPolicy
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
    # L'en-tête nomme **toutes** les opérations du module, quelle que soit sa
    # classe. Un module de gestion en porte deux, la lecture et l'écriture, et
    # les omettre laissait un en-tête vide dont `ansible-test` signalait
    # l'espace en fin de ligne plutôt que le vrai défaut.
    operations = [
        operation.id
        for operation in (
            spec.get_operation,
            spec.list_operation,
            spec.action_operation,
            spec.read_operation,
            spec.update_operation,
        )
        if operation is not None
    ]

    rendered = template.render(
        generated_header=GENERATED_HEADER,
        authors=", ".join(spec.collection.authors) or spec.collection.fqcn,
        source=source,
        operations=", ".join(operations),
        documentation=_yaml_block(spec.documentation()),
        examples=_examples_block(spec),
        returns=_yaml_block(spec.return_documentation()),
        module_utils_import=spec.collection.module_utils_import,
        runtime_imports=_runtime_imports(spec),
        common_argument_specs=_common_argument_specs(spec),
        argument_spec=python_literal(spec.argument_spec()),
        module_literal=_module_literal(spec),
        run_call=_run_call(spec),
        omission_declaration=_omission_declaration(spec),
        exclusive_declaration=_exclusive_declaration(spec),
        module_arguments=_module_arguments(spec),
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
    OperationKind.MANAGE: "run_manage_module",
}

#: La dataclasse de description que chaque classe déclare.
_SPEC_CLASSES: dict[OperationKind, str] = {
    OperationKind.INFO: "InfoModule",
    OperationKind.ACTION: "ActionModule",
    OperationKind.MANAGE: "ManageModule",
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
    if spec.nullable_params:
        noms.add("poser_les_temoins")
    return sorted(noms)


def _common_argument_specs(spec: AnsibleModuleSpec) -> list[str]:
    """Les jeux de paramètres communs que le module assemble, dans l'ordre."""
    appels = ["scaleway_argument_spec()"]
    if spec.waitable:
        appels.append("scaleway_waitable_argument_spec()")
    return appels


def _exclusive_declaration(spec: AnsibleModuleSpec) -> str:
    """La constante des groupes exclusifs, ou rien quand il n'y en a pas.

    Elle est nommée plutôt qu'écrite dans l'appel : un lecteur du module voit
    d'un coup ce que l'API interdit d'utiliser ensemble, sans démonter un appel
    de fonction.
    """
    groupes = spec.exclusion_groups()
    if not groupes:
        return ""
    return (
        "#: Ce que l'API interdit d'utiliser ensemble, déclaré par le contrat.\n"
        f"MUTUALLY_EXCLUSIVE = {python_literal([list(groupe) for groupe in groupes])}\n"
        "\n\n"
    )


def _module_arguments(spec: AnsibleModuleSpec) -> str:
    """Les arguments d'`AnsibleModule`, sur une ligne ou sur plusieurs.

    Un module sans contrainte garde la forme d'une ligne qu'il avait déjà : le
    diff de génération ne montre alors que les modules réellement concernés,
    et `mise run check:generated` reste lisible.
    """
    if not spec.exclusion_groups():
        return "argument_spec=ARGUMENT_SPEC, supports_check_mode=True"
    return (
        "\n        argument_spec=ARGUMENT_SPEC,"
        "\n        supports_check_mode=True,"
        "\n        mutually_exclusive=MUTUALLY_EXCLUSIVE,"
        "\n    "
    )


def _omission_declaration(spec: AnsibleModuleSpec) -> str:
    """La pose des témoins d'omission, ou rien quand aucun champ n'est effaçable.

    Elle est dans le fichier généré, et pas cachée dans le runtime : un lecteur
    du module doit voir que quelque chose est posé sur son `argument_spec` avant
    qu'Ansible le lise. L'ensemble est vide à cette ligne et se remplit pendant
    la construction d'`AnsibleModule` (ADR-016).
    """
    if not spec.nullable_params:
        return ""
    return (
        "\n"
        "#: Ce que le contrat déclare effaçable. Ansible n'appelle un `fallback`\n"
        "#: que sur une clé absente de l'invocation : le témoin note le nom sans\n"
        "#: rien injecter, ce qui sépare `champ: null` de `champ` omis.\n"
        "OMISSIONS = poser_les_temoins(ARGUMENT_SPEC, MODULE.nullable_params)\n"
    )


def _run_call(spec: AnsibleModuleSpec) -> str:
    if spec.nullable_params:
        return f"{_RUN_FUNCTIONS[spec.kind]}(module, MODULE, OMISSIONS)"
    return f"{_RUN_FUNCTIONS[spec.kind]}(module, MODULE)"


def _module_literal(spec: AnsibleModuleSpec) -> str:
    """Rend la déclaration que le module généré porte, selon sa classe."""
    if spec.kind is OperationKind.ACTION:
        return _action_module_literal(spec)
    if spec.kind is OperationKind.MANAGE:
        return _manage_module_literal(spec)
    return _info_module_literal(spec)


def _action_module_literal(spec: AnsibleModuleSpec) -> str:
    """Rend l'appel `ActionModule(...)`."""
    if spec.action_operation is None:
        raise RenderError(f"{spec.name} : module d'action sans opération à déclencher")

    lines = ["ActionModule("]
    lines.append(f"    operation={_operation_literal(spec.action_operation, indent=4)},")
    # `None` quand l'action est l'opération elle-même : le runtime rend alors
    # l'identifiant de l'opération plutôt que la valeur d'une option absente.
    if spec.action_parameter is None:
        lines.append("    action_parameter=None,")
    else:
        lines.append(f"    action_parameter={quote(spec.action_parameter)},")
    if spec.read_operation is not None:
        lines.append(f"    read_operation={_operation_literal(spec.read_operation, indent=4)},")
    if spec.wait_states:
        lines.append(f"    state_field={quote(spec.state_field)},")
        etats = dict(spec.wait_states)
        lines.append(f"    wait_states={python_literal(etats, indent=4)},")
    lines.append(")")
    return "\n".join(lines)


def _manage_module_literal(spec: AnsibleModuleSpec) -> str:
    """Rend l'appel `ManageModule(...)`."""
    if spec.update_operation is None or spec.read_operation is None:
        raise RenderError(f"{spec.name} : module de gestion sans lecture ou sans écriture")

    lines = ["ManageModule("]
    lines.append(f"    read_operation={_operation_literal(spec.read_operation, indent=4)},")
    lines.append(f"    update_operation={_operation_literal(spec.update_operation, indent=4)},")
    lines.append(f"    managed_params={python_literal(spec.managed_params, indent=4)},")
    lines.append(f"    comparisons={python_literal(spec.comparisons, indent=4)},")
    if spec.unverified_params:
        lines.append(f"    unverified_params={python_literal(spec.unverified_params, indent=4)},")
    if spec.secret_params:
        lines.append(f"    secret_params={python_literal(spec.secret_params, indent=4)},")
    if spec.nullable_params:
        lines.append(f"    nullable_params={python_literal(spec.nullable_params, indent=4)},")
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


def _examples_block(spec: AnsibleModuleSpec) -> str:
    """Le préambule en commentaires, puis les tâches.

    YAML ne porte pas de commentaire à travers `safe_dump` : le texte se
    préfixe ici, une fois le bloc sérialisé. Une ligne vide du préambule devient
    un `#` seul plutôt qu'une ligne blanche, sinon le commentaire se coupe en
    deux blocs et le second flotte au-dessus des tâches.
    """
    taches = _yaml_block(spec.examples_documentation())
    preambule = spec.examples_preamble()
    if not preambule:
        return taches
    entete = "\n".join(f"# {ligne}".rstrip() for ligne in preambule)
    return f"{entete}\n\n{taches}"


class _SansAncre(yaml.SafeDumper):
    """Un sérialiseur qui n'écrit jamais d'ancre YAML.

    **Un exemple se copie tâche par tâche.** Deux tâches qui partagent une
    valeur, comme la tâche d'écriture et sa simulation, faisaient écrire
    `tags: &id001` à la première et `tags: *id001` à la seconde : du YAML
    parfaitement valide, que personne ne peut copier séparément, et dont la
    seconde tâche ne dit plus ce qu'elle envoie.

    Le golden l'a montré à la ligne près. Rendre une valeur deux fois coûte
    quelques octets ; une page publiée qu'on ne peut pas copier coûte le service
    qu'elle est censée rendre.
    """

    def ignore_aliases(self, data: Any) -> bool:
        return True


def _yaml_block(payload: Any) -> str:
    """Sérialise un bloc de documentation en YAML, sans réordonner les clés.

    L'ordre vient du modèle : il est celui d'une lecture humaine, et le trier
    alphabétiquement mettrait `author` avant `description`.
    """
    text = yaml.dump(
        payload,
        Dumper=_SansAncre,
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

    # Un dictionnaire de scalaires reste sur la ligne de la séquence qui le
    # porte : `("name", {"type": "str"})` se lit d'un coup, déplié sur quatre
    # lignes il noie le nom sous sa forme.
    morceaux: list[str] = []
    for item in value:
        if _is_scalar(item):
            morceaux.append(_scalar_literal(item))
            continue
        if isinstance(item, dict) and item and all(_is_scalar(v) for v in item.values()):
            morceaux.append(_inline_literal(item) or "")
            continue
        return None
    body = ", ".join(morceaux)
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
    if operation.csv_params:
        fields.append(("csv_params", operation.csv_params))
    if operation.payload_field is not None:
        fields.append(("payload_field", operation.payload_field))
    if operation.is_list:
        fields.append(("is_list", True))
    if operation.page_param is not None:
        fields.append(("page_param", operation.page_param))
    if operation.per_page_param is not None:
        fields.append(("per_page_param", operation.per_page_param))
    # Le défaut du runtime est `never`, le plus prudent : l'omettre sur une
    # action, c'est écrire la même chose plus court, et le diff de génération
    # ne montre alors que les opérations qui autorisent vraiment un réessai.
    if operation.retry is not RetryPolicy.NEVER:
        fields.append(("retry", operation.retry.value))

    lines = ["Operation("]
    for name, value in fields:
        lines.append(f"{inner}{name}={python_literal(value, indent=indent + 4)},")
    lines.append(pad + ")")
    return "\n".join(lines)
