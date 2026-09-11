"""Rejouer le parcours d'accueil, pour qu'il ne périme pas en silence.

Le quickstart est la première chose qu'un visiteur exécute, et une page
d'accueil dont les commandes ne marchent plus coûte le visiteur, pas une
minute. Ce lanceur joue le parcours que `quickstart/README.md` décrit, et
**mesure ce que chaque étape doit prouver** plutôt que de constater qu'elle
sort en 0.

Trois vérifications ont une valeur particulière, parce qu'elles distinguent un
parcours qui marche d'un parcours qui se contente de ne pas échouer :

* le diagnostic rend `ok` sur **chacun** de ses contrôles. Un `?` n'y passe
  pas pour un succès, et sortir en 0 ne suffit pas ;
* le second passage du playbook d'étiquettes rend `changed=0`. C'est toute la
  démonstration : un module qui lit, compare, et n'écrit que la différence ;
* le redémarrage progressif a **observé** chaque machine partir et revenir. Un
  redémarrage qui n'attendrait pas sortirait en 0 lui aussi.

Codes de sortie : `0` le parcours tient, `1` le lanceur n'a pas pu le jouer,
`2` il l'a joué et le verdict est non.
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
QUICKSTART = ROOT / "quickstart"


class QuickstartError(Exception):
    """Le lanceur n'a pas pu jouer le parcours."""


class Verdict(Exception):
    """Le parcours a été joué, et il ne tient pas."""


def compose(*arguments: str, capture: bool = False) -> subprocess.CompletedProcess[str]:
    binaire = shutil.which("docker")
    if not binaire:
        raise QuickstartError(
            "docker est introuvable. Ce parcours est celui qu'un visiteur joue "
            "avec docker : le rejouer autrement ne mesurerait pas la même chose."
        )
    return subprocess.run(
        [binaire, "compose", *arguments],
        cwd=QUICKSTART,
        capture_output=capture,
        text=True,
        check=False,
    )


def jouer(commande: str) -> str:
    """Une commande du parcours, avec les identifiants que l'émulateur sert.

    La ligne est celle de la page, à la source des identifiants près : la page
    la donne sous sa forme `docker compose run`, et c'est bien elle qui tourne.
    """
    resultat = compose(
        "run",
        "--rm",
        "ansible",
        "sh",
        "-c",
        f". /env/scaleway.sh && {commande}",
        capture=True,
    )
    sortie = resultat.stdout + resultat.stderr
    if resultat.returncode != 0:
        raise Verdict(f"`{commande}` a échoué :\n{sortie[-2000:]}")
    return sortie


def changements(sortie: str) -> int:
    """Le `changed=` du récapitulatif, lu plutôt que supposé."""
    trouve = re.search(r"^localhost\s+:.*?changed=(\d+)", sortie, flags=re.MULTILINE)
    if trouve is None:
        raise Verdict(
            "aucun récapitulatif dans la sortie : le playbook n'a pas joué, et "
            f"un parcours qui ne joue pas ne prouve rien.\n{sortie[-1000:]}"
        )
    return int(trouve.group(1))


#: Une ligne du rapport de diagnostic : son verdict, puis ce qu'il porte.
_CONTROLE = re.compile(r'"(ok|ko|\?)\s+(.+?)",?$', re.MULTILINE)


#: Les zones où le parc fictif vit. Les nommer plutôt que de laisser le
#: rapport interroger tout le catalogue : une zone que l'émulateur ne sert pas
#: est honnêtement rendue « non mesurée », et un parcours d'accueil n'a pas à
#: enseigner ce cas-là avant d'avoir montré le cas courant.
ZONES = "fr-par-1,fr-par-2"


def etape_diagnostic() -> None:
    """Le verdict se lit dans les contrôles, pas dans la phrase qui les résume.

    Le playbook conclut par un `assert` dont le `success_msg` vaut `Ready.`, et
    le callback par défaut **ne l'imprime pas**. Chercher cette phrase aurait
    mesuré l'affichage d'Ansible plutôt que l'état de la machine, et ce parcours
    aurait rougi pour une raison sans rapport avec ce qu'il prouve.

    Ce que `Ready` veut dire est ici : chaque contrôle a rendu `ok`, et `?` n'y
    passe pas pour un succès. Une API injoignable n'est pas un compte prêt.
    """
    sortie = jouer("ansible-playbook stephrobert.scaleway.doctor")
    controles = _CONTROLE.findall(sortie)
    if not controles:
        raise Verdict(f"le diagnostic ne rend aucun contrôle :\n{sortie[-1500:]}")

    refuses = [f"{verdict} {detail}" for verdict, detail in controles if verdict != "ok"]
    if refuses:
        raise Verdict(
            "le diagnostic ne dit pas que tout va : " + " · ".join(refuses) + ". "
            "Un `?` n'est pas un succès, c'est un contrôle qui n'a pas pu se faire."
        )
    # Le détail, pas seulement le compte : c'est lui qui dit quelle zone répond
    # et combien de machines elle porte, et c'est précisément ce qui manquait
    # pour comprendre un premier échec en CI.
    print("  diagnostic :")
    for _, detail in controles:
        print(f"    ok  {detail}")


def etape_rapport() -> None:
    """Un total nul n'accuse pas forcément le parc, et le dire compte.

    Le rapport **nomme** les zones qui n'ont pas répondu plutôt que de les
    compter zéro. Un verdict qui lirait « total nul » et conclurait « le parc
    est vide » se tromperait de coupable, et c'est ce qu'il a fait la première
    fois : le peuplement avait créé ses cinq machines, et le rapport
    interrogeait dix zones dont deux muettes.
    """
    sortie = jouer(f"ansible-playbook stephrobert.scaleway.fleet_report -e zones={ZONES}")
    if "instances_by_state" not in sortie:
        raise Verdict(f"le rapport de parc ne rend pas son inventaire :\n{sortie[-1500:]}")

    if '"instances_total": "0"' in sortie:
        muettes = re.search(r'"zones_unmeasured": \[(.*?)\]', sortie, flags=re.DOTALL)
        cause = (
            f"les zones {' '.join(muettes.group(1).split())} n'ont pas répondu"
            if muettes and muettes.group(1).strip()
            else "toutes les zones ont répondu, et le parc y est vide"
        )
        raise Verdict(f"le rapport ne voit aucune machine, et {cause}.\n{sortie[-2500:]}")
    print("  rapport de parc : le parc est vu")


def etape_inventaire() -> None:
    sortie = jouer("ansible-inventory --graph")
    groupes = set(re.findall(r"@(scw_[a-z0-9_]+):", sortie))
    attendus = {"scw_tag_office_hours", "scw_state_running", "scw_zone_fr_par_1"}
    manquants = sorted(attendus - groupes)
    if manquants:
        raise Verdict(
            f"l'inventaire dynamique ne construit plus {manquants}. Ce sont les "
            "groupes sur lesquels les commandes de la page agissent."
        )
    print(f"  inventaire : {len(groupes)} groupe(s) découvert(s)")


def etape_idempotence() -> None:
    """Le cœur de la démonstration, et la seule étape jouée deux fois."""
    premier = changements(jouer("ansible-playbook etiquettes.yml"))
    second = changements(jouer("ansible-playbook etiquettes.yml"))

    if second != 0:
        raise Verdict(
            f"le second passage rend changed={second}. La page promet un module "
            "qui lit, compare et n'écrit que la différence : c'est précisément "
            "ce qui vient de ne pas tenir."
        )
    # Un premier passage déjà muet dirait que l'étape ne mesure rien : elle
    # passerait sur une plateforme où la machine porte déjà les étiquettes.
    if premier == 0:
        raise Verdict(
            "le premier passage ne change rien non plus : la démonstration "
            "compare un état à lui-même, et le second `changed=0` ne prouve rien."
        )
    print(f"  étiquettes : changed={premier} puis changed={second}")


def etape_redemarrage() -> None:
    sortie = jouer(
        "ansible-playbook stephrobert.scaleway.rolling_reboot "
        "-e group=scw_tag_role_web -e batch_size=1"
    )
    if "RETRYING" not in sortie:
        raise Verdict(
            "aucune attente observée pendant le redémarrage. Le playbook promet "
            "de regarder chaque machine quitter `running` et revenir ; une "
            f"boucle qui n'attend jamais a conclu sans rien observer.\n{sortie[-2000:]}"
        )
    if not re.search(r"\d+ rebooted", sortie):
        raise Verdict(f"le redémarrage ne dit pas ce qu'il a fait :\n{sortie[-1500:]}")
    print("  redémarrage progressif : attente observée, machines revenues")


ETAPES = (
    ("le diagnostic", etape_diagnostic),
    ("le rapport de parc", etape_rapport),
    ("l'inventaire dynamique", etape_inventaire),
    ("l'idempotence", etape_idempotence),
    ("le redémarrage progressif", etape_redemarrage),
)


def etats() -> dict[str, tuple[str, int]]:
    """Ce que chaque service est devenu : son état, et son code de sortie."""
    resultat = compose(
        "ps", "-a", "--format", "{{.Service}} {{.State}} {{.ExitCode}}", capture=True
    )
    trouves: dict[str, tuple[str, int]] = {}
    for ligne in resultat.stdout.splitlines():
        morceaux = ligne.split()
        if len(morceaux) == 3:
            trouves[morceaux[0]] = (morceaux[1], int(morceaux[2]))
    return trouves


def journal(service: str) -> str:
    return compose("logs", "--no-color", service, capture=True).stdout[-3000:]


def identite(service: str) -> str:
    """L'identifiant du conteneur, pour qu'un remplacement se voie.

    Un conteneur recréé entre deux commandes emporte ce qu'il gardait en
    mémoire. L'état de l'émulateur est désormais un fichier, donc ça ne coûte
    plus la flotte ; le dire reste utile, parce qu'une identité qui change
    explique des choses qu'on chercherait longtemps autrement.
    """
    return compose("ps", "-aq", service, capture=True).stdout.strip()[:12] or "absent"


def demarrer() -> None:
    """La commande de la page, puis l'attente que `--wait` ne donne pas.

    `docker compose up -d` est bien ce qu'un visiteur tape, et c'est pour ça que
    c'est cette commande-là qui tourne. Mais **`--wait` n'attend pas la fin d'un
    service qui sort** : mesuré en CI, il rend la main pendant que le peuplement
    tourne encore, et le parcours partait alors sur un parc vide en accusant la
    collection. L'attente est donc explicite, et elle porte sur le fait qui
    compte : le peuplement est sorti, et il est sorti en 0.
    """
    print("démarrage de l'émulateur et peuplement du parc")
    resultat = compose("up", "-d", "--wait", capture=True)

    limite = time.monotonic() + 180
    while True:
        devenus = etats()
        emulateur = devenus.get("emulateur", ("absent", -1))
        parc = devenus.get("parc", ("absent", -1))

        if parc[0] == "exited":
            if parc[1] != 0:
                raise QuickstartError(
                    f"le peuplement du parc a échoué (code {parc[1]}). Ce n'est pas "
                    f"un verdict sur la collection :\n{journal('parc')}"
                )
            if emulateur[0] != "running":
                raise QuickstartError(
                    f"l'émulateur n'est plus en écoute ({emulateur[0]}) :\n{journal('emulateur')}"
                )
            print(f"  émulateur {identite('emulateur')}, parc peuplé et relu")
            return

        if time.monotonic() > limite:
            raise QuickstartError(
                f"le peuplement n'a pas abouti : émulateur {emulateur}, parc {parc}.\n"
                f"{journal('parc')}\n"
                f"`up --wait` avait rendu {resultat.returncode} :\n"
                f"{(resultat.stdout + resultat.stderr)[-1500:]}"
            )
        time.sleep(2)


def arreter() -> None:
    """Toujours, y compris après un échec : un parcours ne laisse rien debout.

    Rien n'est facturé ici, mais un volume qui survit garde le parc d'hier, et
    la démonstration d'idempotence mesurerait alors le run précédent.
    """
    compose("down", "-v", capture=True)


def main(argv: list[str]) -> int:
    parseur = argparse.ArgumentParser(description="Rejouer le parcours d'accueil.")
    parseur.add_argument(
        "--garder",
        action="store_true",
        help="ne pas détruire la composition à la fin, pour diagnostiquer sur place",
    )
    arguments = parseur.parse_args(argv)

    try:
        demarrer()
        print("le parcours, étape par étape")
        for nom, etape in ETAPES:
            try:
                etape()
            except Verdict as erreur:
                print(f"\n{nom} ne tient pas : {erreur}", file=sys.stderr)
                # **Un échec muet coûte un aller-retour complet.** La première
                # exécution en CI a rendu « le parc est vide » sans une ligne de
                # ce que le peuplement avait fait, et la sortie de compose était
                # là, capturée et jetée.
                print(
                    f"\n--- l'émulateur est {identite('emulateur')} ---",
                    file=sys.stderr,
                )
                print(f"\n--- ce que le peuplement a dit ---\n{journal('parc')}", file=sys.stderr)
                print(
                    f"\n--- ce que l'émulateur a dit ---\n{journal('emulateur')}", file=sys.stderr
                )
                return 2
    except QuickstartError as erreur:
        print(f"\nle parcours n'a pas pu être joué : {erreur}", file=sys.stderr)
        return 1
    finally:
        if not arguments.garder:
            arreter()

    print("\nle parcours d'accueil tient, de bout en bout, sans compte Scaleway.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
