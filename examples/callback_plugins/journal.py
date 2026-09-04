"""Enregistre ce qu'une exécution a réellement joué, module par module.

Un run contre le compte Scaleway réel ne laissait rien derrière lui. Le lanceur
imprimait son compte rendu sur la sortie standard, et la sortie standard
disparaît avec le terminal : on ne pouvait donc pas dire si la collection avait
jamais été éprouvée sur une opération donnée, ni quand.

**Pourquoi un plugin de rappel plutôt qu'une lecture du playbook.** Analyser le
YAML dirait ce que le playbook *appelle*, pas ce qui s'est *joué* : une tâche
gardée par un `when` non satisfait ne touche jamais l'API, et la compter comme
exercée serait exactement la couverture maquillée que ce dépôt refuse ailleurs.
Ansible connaît la différence, et c'est lui qu'on écoute.

Le journal capture aussi les faits du recensement, `idempotences_prouvees` et
`reecritures_non_mesurees`, parce qu'ils passent par `set_fact` et qu'un
`set_fact` est un résultat de tâche comme un autre. Rien à ajouter au playbook.

    ANSIBLE_CALLBACK_PLUGINS=examples/callback_plugins \\
    ANSIBLE_CALLBACKS_ENABLED=journal \\
    EXEMPLE_JOURNAL=build/example/journal.json \\
    ansible-playbook ...

Sans `EXEMPLE_JOURNAL`, le plugin ne fait rien : il ne doit pas changer le
comportement d'une exécution que personne n'a instrumentée.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from ansible.plugins.callback import CallbackBase

DOCUMENTATION = """
    name: journal
    type: aggregate
    short_description: Écrit ce qu'une exécution a joué dans un fichier JSON
    description:
      - Enregistre chaque tâche jouée avec son module et son verdict, et les
        faits du recensement, dans le fichier nommé par C(EXEMPLE_JOURNAL).
    requirements:
      - la variable d'environnement EXEMPLE_JOURNAL
"""

#: Les faits du recensement, repris tels quels dans le journal.
FAITS_SUIVIS = (
    "non_emules",
    "noms_repris",
    "reecritures_non_mesurees",
    "idempotences_prouvees",
)


class CallbackModule(CallbackBase):
    """Un journal d'exécution, écrit une fois à la fin du jeu."""

    CALLBACK_VERSION = 2.0
    CALLBACK_TYPE = "aggregate"
    CALLBACK_NAME = "journal"
    CALLBACK_NEEDS_ENABLED = True

    def __init__(self) -> None:
        super().__init__()
        chemin = os.environ.get("EXEMPLE_JOURNAL")
        self._destination = Path(chemin) if chemin else None
        self._taches: list[dict[str, Any]] = []
        self._faits: dict[str, Any] = {}

    # --- ce qui se joue -----------------------------------------------------

    def _noter(self, result: Any, verdict: str) -> None:
        if self._destination is None:
            return
        brut = result._result if isinstance(result._result, dict) else {}
        self._taches.append(
            {
                "module": result._task.action,
                "tache": result._task.get_name(),
                "verdict": verdict,
                "changed": bool(brut.get("changed", False)),
                # Une route que l'émulateur ne sert pas n'est pas un échec de la
                # collection, et le journal doit permettre de faire la
                # différence sans relire les 800 lignes du playbook.
                "api_type": brut.get("api_type"),
            }
        )
        for nom, valeur in (brut.get("ansible_facts") or {}).items():
            if nom in FAITS_SUIVIS:
                self._faits[nom] = valeur

    def v2_runner_on_ok(self, result: Any) -> None:
        self._noter(result, "changed" if result._result.get("changed") else "ok")

    def v2_runner_on_failed(self, result: Any, ignore_errors: bool = False) -> None:
        self._noter(result, "ignored" if ignore_errors else "failed")

    def v2_runner_on_skipped(self, result: Any) -> None:
        self._noter(result, "skipped")

    # --- ce qu'on en garde --------------------------------------------------

    def v2_playbook_on_stats(self, stats: Any) -> None:
        if self._destination is None:
            return
        self._destination.parent.mkdir(parents=True, exist_ok=True)
        # Fusionne plutôt que d'écraser : le lanceur joue trois playbooks à la
        # suite, chacun dans son propre processus, et le journal doit dire ce
        # que l'exercice entier a couvert.
        anterieur: dict[str, Any] = {}
        if self._destination.is_file():
            try:
                anterieur = json.loads(self._destination.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                anterieur = {}
        taches = list(anterieur.get("taches", [])) + self._taches
        faits = {**anterieur.get("faits", {}), **self._faits}
        self._destination.write_text(
            json.dumps({"taches": taches, "faits": faits}, indent=2, ensure_ascii=False, sort_keys=True)
            + "\n",
            encoding="utf-8",
        )
