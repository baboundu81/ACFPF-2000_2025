# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright (C) 2026 ACFPF contributors

"""Regression fixtures based on the 2026 Assemblée nationale dossier JSON schema."""

from acfpf.data.assemblee_legislation import parse_assembly_dossier


def test_nested_official_act_label_generates_dated_legislative_event() -> None:
    dossier = parse_assembly_dossier(
        {
            "dossierParlementaire": {
                "uid": "DLR5L17N54629",
                "legislature": "17",
                "titreDossier": {
                    "titre": "Projet de loi de finances pour 2027",
                    "titreChemin": "PLF_2027",
                },
                "actesLegislatifs": {
                    "acteLegislatif": {
                        "codeActe": "AN1",
                        "libelleActe": {
                            "nomCanonique": "1ère lecture (1ère assemblée saisie)",
                            "libelleCourt": "1ère lecture",
                        },
                        "dateActe": None,
                        "actesLegislatifs": {
                            "acteLegislatif": {
                                "uid": "L17-VD233892DI",
                                "codeActe": "AN1-DEPOT",
                                "libelleActe": {
                                    "nomCanonique": "1er dépôt d'une initiative.",
                                    "libelleCourt": "Dépôt initial",
                                },
                                "dateActe": "2026-10-01T00:00:00.000+02:00",
                                "texteAssocie": "PRJLANR5L17B3210",
                            }
                        },
                    }
                },
            }
        }
    )

    assert len(dossier.events) == 2
    assert dossier.events[0].label == "1ère lecture"
    assert dossier.events[0].code == "AN1"
    assert dossier.events[1].label == "Dépôt initial"
    assert dossier.events[1].code == "AN1-DEPOT"
    assert dossier.events[1].date == "2026-10-01"
    assert dossier.last_activity == "2026-10-01"
