{
  "data": {
    "hs_code": "7208510000",
    "description": "HS 7208510000",
    "origin_country": "GB",
    "origin_input": "GB",
    "destination_country": "DE",
    "destination_market": "EU",
    "origin": {
      "origin_code": "GB",
      "origin_name": "GB",
      "origin_code_type": "country",
      "iso2": "GB",
      "iso3": null,
      "is_erga_omnes": false,
      "is_group": false,
      "group_category": null,
      "exists": true,
      "member_countries": [
        "GB"
      ]
    },
    "origin_resolution": [
      {
        "origin_code": "GB",
        "exists": true,
        "origin_name": "GB",
        "origin_code_type": "country",
        "is_group": false,
        "is_erga_omnes": false,
        "group_category": null
      },
      {
        "origin_code": "1008",
        "exists": true,
        "origin_name": "All third countries",
        "origin_code_type": "group_numeric",
        "is_group": true,
        "is_erga_omnes": false,
        "group_category": "other"
      },
      {
        "origin_code": "1011",
        "exists": true,
        "origin_name": "ERGA OMNES",
        "origin_code_type": "erga_omnes",
        "is_group": false,
        "is_erga_omnes": true,
        "group_category": "erga_omnes"
      }
    ],
    "rates_by_origin": [
      {
        "origin_code": "GB",
        "origin_name": "GB",
        "origin_code_type": "country",
        "rate_basis": "bilateral_preference",
        "rate_type": "PREFERENTIAL",
        "duty_rate": 0,
        "duty_amount": null,
        "duty_unit": null,
        "valid_from": "2021-01-01",
        "valid_to": null,
        "source": "TARIC",
        "duty_expression": "0.000 %",
        "human_readable": "0%",
        "conditions": []
      },
      {
        "origin_code": "1008",
        "origin_name": "All third countries",
        "origin_code_type": "group_numeric",
        "rate_basis": "import_control",
        "rate_type": "IMPORT_CONTROL",
        "duty_rate": null,
        "duty_amount": null,
        "duty_unit": null,
        "valid_from": "2023-12-19",
        "valid_to": "2026-12-31",
        "source": "TARIC",
        "duty_expression": "Cond:  Y cert: L-139 (29):; Y cert: Y-824 (29):; Y cert: Y-878 (29):; Y cert: Y-859 (29):; Y cert: L-143 (29):; Y (09):",
        "human_readable": "See conditions",
        "conditions": [
          {
            "condition_type": "Y",
            "condition_logic": "ANY_SUFFICIENT",
            "certificate_code": "L-139",
            "certificate_description": "Unknown — code L-139",
            "duty_expression_code": "29",
            "duty_rate_if_met": null,
            "duty_rate_if_not_met": null,
            "note": "This measure does NOT apply if any one of the listed certificates is presented."
          },
          {
            "condition_type": "Y",
            "condition_logic": "ANY_SUFFICIENT",
            "certificate_code": "Y-824",
            "certificate_description": "Unknown — code Y-824",
            "duty_expression_code": "29",
            "duty_rate_if_met": null,
            "duty_rate_if_not_met": null,
            "note": "This measure does NOT apply if any one of the listed certificates is presented."
          },
          {
            "condition_type": "Y",
            "condition_logic": "ANY_SUFFICIENT",
            "certificate_code": "Y-878",
            "certificate_description": "Unknown — code Y-878",
            "duty_expression_code": "29",
            "duty_rate_if_met": null,
            "duty_rate_if_not_met": null,
            "note": "This measure does NOT apply if any one of the listed certificates is presented."
          },
          {
            "condition_type": "Y",
            "condition_logic": "ANY_SUFFICIENT",
            "certificate_code": "Y-859",
            "certificate_description": "Unknown — code Y-859",
            "duty_expression_code": "29",
            "duty_rate_if_met": null,
            "duty_rate_if_not_met": null,
            "note": "This measure does NOT apply if any one of the listed certificates is presented."
          },
          {
            "condition_type": "Y",
            "condition_logic": "ANY_SUFFICIENT",
            "certificate_code": "L-143",
            "certificate_description": "Unknown — code L-143",
            "duty_expression_code": "29",
            "duty_rate_if_met": null,
            "duty_rate_if_not_met": null,
            "note": "This measure does NOT apply if any one of the listed certificates is presented."
          },
          {
            "condition_type": "Y",
            "condition_logic": "ANY_SUFFICIENT",
            "certificate_code": null,
            "certificate_description": null,
            "duty_expression_code": "09",
            "duty_rate_if_met": null,
            "duty_rate_if_not_met": null,
            "note": "This measure does NOT apply if any one of the listed certificates is presented."
          }
        ]
      },
      {
        "origin_code": "1011",
        "origin_name": "ERGA OMNES",
        "origin_code_type": "erga_omnes",
        "rate_basis": "MFN",
        "rate_type": "MFN",
        "duty_rate": 0,
        "duty_amount": null,
        "duty_unit": null,
        "valid_from": "2005-01-01",
        "valid_to": null,
        "source": "TARIC",
        "duty_expression": "0.000 %",
        "human_readable": "0%",
        "conditions": []
      }
    ],
    "best_rate": {
      "origin_code": "GB",
      "rate_basis": "bilateral_preference",
      "duty_rate": 0,
      "saving_vs_mfn": 0,
      "saving_pct": null
    },
    "available_origin_codes": [
      "1008",
      "1011",
      "1033",
      "1034",
      "1035",
      "2000",
      "2005",
      "5005",
      "CI",
      "CM",
      "EG",
      "FJ",
      "GB",
      "GH",
      "ID",
      "IL",
      "IN",
      "JO",
      "KE",
      "KP",
      "KR",
      "LB",
      "MA",
      "PG",
      "PS",
      "RU",
      "SB",
      "TN",
      "TR",
      "UA",
      "WS",
      "XC",
      "XL"
    ],
    "origin_matrix": [
      {
        "origin_code": "1008",
        "origin_name": "All third countries",
        "origin_code_type": "group_numeric",
        "measure_types": [
          "IMPORT_CONTROL"
        ],
        "records": [
          {
            "hs_code": "7208510000",
            "market": "EU",
            "origin_code": "1008",
            "origin_name": "All third countries",
            "origin_code_type": "group_numeric",
            "measure_type": "IMPORT_CONTROL",
            "rate_basis": "import_control",
            "duty_rate": null,
            "duty_amount": null,
            "rate_specific_unit": null,
            "valid_from": "2023-12-19",
            "valid_to": "2026-12-31",
            "source": "TARIC",
            "ingested_at": "2026-03-29T02:19:46.912261+00:00",
            "details": {
              "measure_type_text": "Import control",
              "measure_type_code": "763",
              "origin_text": "All third countries",
              "origin_code_raw": "1008",
              "legal_base": "Regulation 0833/14",
              "regulation": null,
              "additional_code": null,
              "order_no": null,
              "duty_text": "Cond:  Y cert: L-139 (29):; Y cert: Y-824 (29):; Y cert: Y-878 (29):; Y cert: Y-859 (29):; Y cert: L-143 (29):; Y (09):"
            }
          }
        ]
      },
      {
        "origin_code": "1011",
        "origin_name": "ERGA OMNES",
        "origin_code_type": "erga_omnes",
        "measure_types": [
          "MFN",
          "SUSPENSION"
        ],
        "records": [
          {
            "hs_code": "7208000000",
            "market": "EU",
            "origin_code": "1011",
            "origin_name": "ERGA OMNES",
            "origin_code_type": "erga_omnes",
            "measure_type": "SUSPENSION",
            "rate_basis": "MFN",
            "duty_rate": 0,
            "duty_amount": null,
            "rate_specific_unit": null,
            "valid_from": "2016-07-01",
            "valid_to": null,
            "source": "TARIC",
            "ingested_at": "2026-03-29T02:19:43.668137+00:00",
            "details": {
              "measure_type_text": "Suspension - goods for certain categories of ships, boats and other vessels and for drilling or production platforms",
              "measure_type_code": "117",
              "origin_text": "ERGA OMNES",
              "origin_code_raw": "1011",
              "legal_base": "Regulation 2658/87",
              "regulation": null,
              "additional_code": null,
              "order_no": null,
              "duty_text": "0.000 %"
            }
          },
          {
            "hs_code": "7208000000",
            "market": "EU",
            "origin_code": "1011",
            "origin_name": "ERGA OMNES",
            "origin_code_type": "erga_omnes",
            "measure_type": "MFN",
            "rate_basis": "MFN",
            "duty_rate": 0,
            "duty_amount": null,
            "rate_specific_unit": null,
            "valid_from": "2005-01-01",
            "valid_to": null,
            "source": "TARIC",
            "ingested_at": "2026-03-29T02:19:43.664808+00:00",
            "details": {
              "measure_type_text": "Third country duty",
              "measure_type_code": "103",
              "origin_text": "ERGA OMNES",
              "origin_code_raw": "1011",
              "legal_base": "Regulation 1789/03",
              "regulation": null,
              "additional_code": null,
              "order_no": null,
              "duty_text": "0.000 %"
            }
          }
        ]
      },
      {
        "origin_code": "1033",
        "origin_name": "1033",
        "origin_code_type": "group_numeric",
        "measure_types": [
          "PREFERENTIAL"
        ],
        "records": [
          {
            "hs_code": "7200000000",
            "market": "EU",
            "origin_code": "1033",
            "origin_name": "1033",
            "origin_code_type": "group_numeric",
            "measure_type": "PREFERENTIAL",
            "rate_basis": "group_preference",
            "duty_rate": 0,
            "duty_amount": null,
            "rate_specific_unit": null,
            "valid_from": "2008-12-29",
            "valid_to": null,
            "source": "TARIC",
            "ingested_at": "2026-03-29T02:19:41.799604+00:00",
            "details": {
              "measure_type_text": "Tariff preference",
              "measure_type_code": "142",
              "origin_text": "CARIFORUM",
              "origin_code_raw": "1033",
              "legal_base": "Decision 0805/08",
              "regulation": null,
              "additional_code": null,
              "order_no": null,
              "duty_text": "0.000 %"
            }
          }
        ]
      },
      {
        "origin_code": "1034",
        "origin_name": "1034",
        "origin_code_type": "group_numeric",
        "measure_types": [
          "PREFERENTIAL"
        ],
        "records": [
          {
            "hs_code": "7200000000",
            "market": "EU",
            "origin_code": "1034",
            "origin_name": "1034",
            "origin_code_type": "group_numeric",
            "measure_type": "PREFERENTIAL",
            "rate_basis": "group_preference",
            "duty_rate": 0,
            "duty_amount": null,
            "rate_specific_unit": null,
            "valid_from": "2012-05-14",
            "valid_to": null,
            "source": "TARIC",
            "ingested_at": "2026-03-29T02:19:41.780391+00:00",
            "details": {
              "measure_type_text": "Tariff preference",
              "measure_type_code": "142",
              "origin_text": "Eastern and Southern Africa States",
              "origin_code_raw": "1034",
              "legal_base": "Decision 0196/12",
              "regulation": null,
              "additional_code": null,
              "order_no": null,
              "duty_text": "0.000 %"
            }
          }
        ]
      },
      {
        "origin_code": "1035",
        "origin_name": "1035",
        "origin_code_type": "group_numeric",
        "measure_types": [
          "PREFERENTIAL"
        ],
        "records": [
          {
            "hs_code": "7200000000",
            "market": "EU",
            "origin_code": "1035",
            "origin_name": "1035",
            "origin_code_type": "group_numeric",
            "measure_type": "PREFERENTIAL",
            "rate_basis": "group_preference",
            "duty_rate": 0,
            "duty_amount": null,
            "rate_specific_unit": null,
            "valid_from": "2016-10-10",
            "valid_to": null,
            "source": "TARIC",
            "ingested_at": "2026-03-29T02:19:41.776204+00:00",
            "details": {
              "measure_type_text": "Tariff preference",
              "measure_type_code": "142",
              "origin_text": "SADC EPA",
              "origin_code_raw": "1035",
              "legal_base": "Decision 1623/16",
              "regulation": null,
              "additional_code": null,
              "order_no": null,
              "duty_text": "0.000 %"
            }
          }
        ]
      },
      {
        "origin_code": "2000",
        "origin_name": "2000",
        "origin_code_type": "group_numeric",
        "measure_types": [
          "PREFERENTIAL"
        ],
        "records": [
          {
            "hs_code": "7200000000",
            "market": "EU",
            "origin_code": "2000",
            "origin_name": "2000",
            "origin_code_type": "group_numeric",
            "measure_type": "PREFERENTIAL",
            "rate_basis": "group_preference",
            "duty_rate": 0,
            "duty_amount": null,
            "rate_specific_unit": null,
            "valid_from": "2025-10-03",
            "valid_to": null,
            "source": "TARIC",
            "ingested_at": "2026-03-29T02:19:41.759381+00:00",
            "details": {
              "measure_type_text": "Tariff preference",
              "measure_type_code": "142",
              "origin_text": "Preferential origin in accordance with the Agreement in the form of an Exchange of Letters between the European Union and the Kingdom of Morocco on the amendment of Protocols 1 and 4 to the Euro-Mediterranean Agreement establishing an association between the European Communities and their Member States, of the one part, and the Kingdom of Morocco, of the other part.",
              "origin_code_raw": "2000",
              "legal_base": "Decision 2022/25",
              "regulation": null,
              "additional_code": null,
              "order_no": null,
              "duty_text": "0.000 %"
            }
          }
        ]
      },
      {
        "origin_code": "2005",
        "origin_name": "2005",
        "origin_code_type": "group_numeric",
        "measure_types": [
          "PREFERENTIAL"
        ],
        "records": [
          {
            "hs_code": "7200000000",
            "market": "EU",
            "origin_code": "2005",
            "origin_name": "2005",
            "origin_code_type": "group_numeric",
            "measure_type": "PREFERENTIAL",
            "rate_basis": "group_preference",
            "duty_rate": 0,
            "duty_amount": null,
            "rate_specific_unit": null,
            "valid_from": "2014-01-01",
            "valid_to": null,
            "source": "TARIC",
            "ingested_at": "2026-03-29T02:19:41.715058+00:00",
            "details": {
              "measure_type_text": "Tariff preference",
              "measure_type_code": "142",
              "origin_text": "GSP-EBA (Special arrangement for the least-developed countries - Everything But Arms)",
              "origin_code_raw": "2005",
              "legal_base": "Regulation 0978/12",
              "regulation": null,
              "additional_code": null,
              "order_no": null,
              "duty_text": "0.000 %"
            }
          }
        ]
      },
      {
        "origin_code": "5005",
        "origin_name": "5005",
        "origin_code_type": "safeguard",
        "measure_types": [
          "SAFEGUARD",
          "TARIFF_QUOTA"
        ],
        "records": [
          {
            "hs_code": "7208510000",
            "market": "EU",
            "origin_code": "5005",
            "origin_name": "5005",
            "origin_code_type": "safeguard",
            "measure_type": "TARIFF_QUOTA",
            "rate_basis": "tariff_quota",
            "duty_rate": 0,
            "duty_amount": null,
            "rate_specific_unit": null,
            "valid_from": "2025-07-08",
            "valid_to": "2026-03-31",
            "source": "TARIC",
            "ingested_at": "2026-03-29T02:19:46.889824+00:00",
            "details": {
              "measure_type_text": "Non preferential tariff quota",
              "measure_type_code": "122",
              "origin_text": "Countries subject to safeguard measures",
              "origin_code_raw": "5005",
              "legal_base": "Regulation 0159/19",
              "regulation": null,
              "additional_code": null,
              "order_no": "098617",
              "duty_text": "0.000 %"
            }
          },
          {
            "hs_code": "7208510000",
            "market": "EU",
            "origin_code": "5005",
            "origin_name": "5005",
            "origin_code_type": "safeguard",
            "measure_type": "SAFEGUARD",
            "rate_basis": "safeguard",
            "duty_rate": 25,
            "duty_amount": null,
            "rate_specific_unit": null,
            "valid_from": "2025-04-01",
            "valid_to": "2026-06-30",
            "source": "TARIC",
            "ingested_at": "2026-03-29T02:19:46.897504+00:00",
            "details": {
              "measure_type_text": "Additional duties (safeguard)",
              "measure_type_code": "696",
              "origin_text": "Countries subject to safeguard measures",
              "origin_code_raw": "5005",
              "legal_base": "Regulation 0159/19",
              "regulation": null,
              "additional_code": null,
              "order_no": null,
              "duty_text": "25.000 %"
            }
          }
        ]
      },
      {
        "origin_code": "CI",
        "origin_name": "CI",
        "origin_code_type": "country",
        "measure_types": [
          "PREFERENTIAL"
        ],
        "records": [
          {
            "hs_code": "7200000000",
            "market": "EU",
            "origin_code": "CI",
            "origin_name": "CI",
            "origin_code_type": "country",
            "measure_type": "PREFERENTIAL",
            "rate_basis": "bilateral_preference",
            "duty_rate": 0,
            "duty_amount": null,
            "rate_specific_unit": null,
            "valid_from": "2019-12-02",
            "valid_to": null,
            "source": "TARIC",
            "ingested_at": "2026-03-29T02:19:41.755777+00:00",
            "details": {
              "measure_type_text": "Tariff preference",
              "measure_type_code": "142",
              "origin_text": "Ivory Coast",
              "origin_code_raw": "CI",
              "legal_base": "Decision 0156/09",
              "regulation": null,
              "additional_code": null,
              "order_no": null,
              "duty_text": "0.000 %"
            }
          }
        ]
      },
      {
        "origin_code": "CM",
        "origin_name": "CM",
        "origin_code_type": "country",
        "measure_types": [
          "PREFERENTIAL"
        ],
        "records": [
          {
            "hs_code": "7200000000",
            "market": "EU",
            "origin_code": "CM",
            "origin_name": "CM",
            "origin_code_type": "country",
            "measure_type": "PREFERENTIAL",
            "rate_basis": "bilateral_preference",
            "duty_rate": 0,
            "duty_amount": null,
            "rate_specific_unit": null,
            "valid_from": "2014-08-04",
            "valid_to": null,
            "source": "TARIC",
            "ingested_at": "2026-03-29T02:19:41.762201+00:00",
            "details": {
              "measure_type_text": "Tariff preference",
              "measure_type_code": "142",
              "origin_text": "Cameroon",
              "origin_code_raw": "CM",
              "legal_base": "Decision 0152/09",
              "regulation": null,
              "additional_code": null,
              "order_no": null,
              "duty_text": "0.000 %"
            }
          }
        ]
      },
      {
        "origin_code": "EG",
        "origin_name": "EG",
        "origin_code_type": "country",
        "measure_types": [
          "PREFERENTIAL"
        ],
        "records": [
          {
            "hs_code": "7200000000",
            "market": "EU",
            "origin_code": "EG",
            "origin_name": "EG",
            "origin_code_type": "country",
            "measure_type": "PREFERENTIAL",
            "rate_basis": "bilateral_preference",
            "duty_rate": 0,
            "duty_amount": null,
            "rate_specific_unit": null,
            "valid_from": "2004-06-01",
            "valid_to": null,
            "source": "TARIC",
            "ingested_at": "2026-03-29T02:19:41.747214+00:00",
            "details": {
              "measure_type_text": "Tariff preference",
              "measure_type_code": "142",
              "origin_text": "Egypt",
              "origin_code_raw": "EG",
              "legal_base": "Decision 0635/04",
              "regulation": null,
              "additional_code": null,
              "order_no": null,
              "duty_text": "0.000 %"
            }
          }
        ]
      },
      {
        "origin_code": "FJ",
        "origin_name": "FJ",
        "origin_code_type": "country",
        "measure_types": [
          "PREFERENTIAL"
        ],
        "records": [
          {
            "hs_code": "7200000000",
            "market": "EU",
            "origin_code": "FJ",
            "origin_name": "FJ",
            "origin_code_type": "country",
            "measure_type": "PREFERENTIAL",
            "rate_basis": "bilateral_preference",
            "duty_rate": 0,
            "duty_amount": null,
            "rate_specific_unit": null,
            "valid_from": "2014-07-28",
            "valid_to": null,
            "source": "TARIC",
            "ingested_at": "2026-03-29T02:19:41.795223+00:00",
            "details": {
              "measure_type_text": "Tariff preference",
              "measure_type_code": "142",
              "origin_text": "Fiji",
              "origin_code_raw": "FJ",
              "legal_base": "Decision 0729/09",
              "regulation": null,
              "additional_code": null,
              "order_no": null,
              "duty_text": "0.000 %"
            }
          }
        ]
      },
      {
        "origin_code": "GB",
        "origin_name": "GB",
        "origin_code_type": "country",
        "measure_types": [
          "PREFERENTIAL"
        ],
        "records": [
          {
            "hs_code": "7200000000",
            "market": "EU",
            "origin_code": "GB",
            "origin_name": "GB",
            "origin_code_type": "country",
            "measure_type": "PREFERENTIAL",
            "rate_basis": "bilateral_preference",
            "duty_rate": 0,
            "duty_amount": null,
            "rate_specific_unit": null,
            "valid_from": "2021-01-01",
            "valid_to": null,
            "source": "TARIC",
            "ingested_at": "2026-03-29T02:19:41.718056+00:00",
            "details": {
              "measure_type_text": "Tariff preference",
              "measure_type_code": "142",
              "origin_text": "United Kingdom",
              "origin_code_raw": "GB",
              "legal_base": "Decision 2253/20",
              "regulation": null,
              "additional_code": null,
              "order_no": null,
              "duty_text": "0.000 %"
            }
          }
        ]
      },
      {
        "origin_code": "GH",
        "origin_name": "GH",
        "origin_code_type": "country",
        "measure_types": [
          "PREFERENTIAL"
        ],
        "records": [
          {
            "hs_code": "7200000000",
            "market": "EU",
            "origin_code": "GH",
            "origin_name": "GH",
            "origin_code_type": "country",
            "measure_type": "PREFERENTIAL",
            "rate_basis": "bilateral_preference",
            "duty_rate": 0,
            "duty_amount": null,
            "rate_specific_unit": null,
            "valid_from": "2016-12-15",
            "valid_to": null,
            "source": "TARIC",
            "ingested_at": "2026-03-29T02:19:41.783366+00:00",
            "details": {
              "measure_type_text": "Tariff preference",
              "measure_type_code": "142",
              "origin_text": "Ghana",
              "origin_code_raw": "GH",
              "legal_base": "Decision 1850/16",
              "regulation": null,
              "additional_code": null,
              "order_no": null,
              "duty_text": "0.000 %"
            }
          }
        ]
      },
      {
        "origin_code": "ID",
        "origin_name": "ID",
        "origin_code_type": "country",
        "measure_types": [
          "TARIFF_QUOTA"
        ],
        "records": [
          {
            "hs_code": "7208510000",
            "market": "EU",
            "origin_code": "ID",
            "origin_name": "ID",
            "origin_code_type": "country",
            "measure_type": "TARIFF_QUOTA",
            "rate_basis": "tariff_quota",
            "duty_rate": 0,
            "duty_amount": null,
            "rate_specific_unit": null,
            "valid_from": "2025-04-01",
            "valid_to": "2026-06-30",
            "source": "TARIC",
            "ingested_at": "2026-03-29T02:19:46.881990+00:00",
            "details": {
              "measure_type_text": "Non preferential tariff quota",
              "measure_type_code": "122",
              "origin_text": "Indonesia",
              "origin_code_raw": "ID",
              "legal_base": "Regulation 0159/19",
              "regulation": null,
              "additional_code": null,
              "order_no": "098426",
              "duty_text": "0.000 %"
            }
          }
        ]
      },
      {
        "origin_code": "IL",
        "origin_name": "IL",
        "origin_code_type": "country",
        "measure_types": [
          "PREFERENTIAL"
        ],
        "records": [
          {
            "hs_code": "7200000000",
            "market": "EU",
            "origin_code": "IL",
            "origin_name": "IL",
            "origin_code_type": "country",
            "measure_type": "PREFERENTIAL",
            "rate_basis": "bilateral_preference",
            "duty_rate": 0,
            "duty_amount": null,
            "rate_specific_unit": null,
            "valid_from": "2023-05-16",
            "valid_to": null,
            "source": "TARIC",
            "ingested_at": "2026-03-29T02:19:41.786262+00:00",
            "details": {
              "measure_type_text": "Tariff preference",
              "measure_type_code": "142",
              "origin_text": "Israel",
              "origin_code_raw": "IL",
              "legal_base": "Decision 0855/09",
              "regulation": null,
              "additional_code": null,
              "order_no": null,
              "duty_text": "0.000 %"
            }
          }
        ]
      },
      {
        "origin_code": "IN",
        "origin_name": "IN",
        "origin_code_type": "country",
        "measure_types": [
          "TARIFF_QUOTA"
        ],
        "records": [
          {
            "hs_code": "7208510000",
            "market": "EU",
            "origin_code": "IN",
            "origin_name": "IN",
            "origin_code_type": "country",
            "measure_type": "TARIFF_QUOTA",
            "rate_basis": "tariff_quota",
            "duty_rate": 0,
            "duty_amount": null,
            "rate_specific_unit": null,
            "valid_from": "2025-04-01",
            "valid_to": "2026-06-30",
            "source": "TARIC",
            "ingested_at": "2026-03-29T02:19:46.878214+00:00",
            "details": {
              "measure_type_text": "Non preferential tariff quota",
              "measure_type_code": "122",
              "origin_text": "India",
              "origin_code_raw": "IN",
              "legal_base": "Regulation 0159/19",
              "regulation": null,
              "additional_code": null,
              "order_no": "098425",
              "duty_text": "0.000 %"
            }
          }
        ]
      },
      {
        "origin_code": "JO",
        "origin_name": "JO",
        "origin_code_type": "country",
        "measure_types": [
          "PREFERENTIAL"
        ],
        "records": [
          {
            "hs_code": "7200000000",
            "market": "EU",
            "origin_code": "JO",
            "origin_name": "JO",
            "origin_code_type": "country",
            "measure_type": "PREFERENTIAL",
            "rate_basis": "bilateral_preference",
            "duty_rate": 0,
            "duty_amount": null,
            "rate_specific_unit": null,
            "valid_from": "2002-05-01",
            "valid_to": null,
            "source": "TARIC",
            "ingested_at": "2026-03-29T02:19:41.743699+00:00",
            "details": {
              "measure_type_text": "Tariff preference",
              "measure_type_code": "142",
              "origin_text": "Jordan",
              "origin_code_raw": "JO",
              "legal_base": "Decision 0357/02",
              "regulation": null,
              "additional_code": null,
              "order_no": null,
              "duty_text": "0.000 %"
            }
          }
        ]
      },
      {
        "origin_code": "KE",
        "origin_name": "KE",
        "origin_code_type": "country",
        "measure_types": [
          "PREFERENTIAL"
        ],
        "records": [
          {
            "hs_code": "7200000000",
            "market": "EU",
            "origin_code": "KE",
            "origin_name": "KE",
            "origin_code_type": "country",
            "measure_type": "PREFERENTIAL",
            "rate_basis": "bilateral_preference",
            "duty_rate": 0,
            "duty_amount": null,
            "rate_specific_unit": null,
            "valid_from": "2024-07-01",
            "valid_to": null,
            "source": "TARIC",
            "ingested_at": "2026-03-29T02:19:41.753072+00:00",
            "details": {
              "measure_type_text": "Tariff preference",
              "measure_type_code": "142",
              "origin_text": "Kenya",
              "origin_code_raw": "KE",
              "legal_base": "Decision 1647/24",
              "regulation": null,
              "additional_code": null,
              "order_no": null,
              "duty_text": "0.000 %"
            }
          }
        ]
      },
      {
        "origin_code": "KP",
        "origin_name": "KP",
        "origin_code_type": "country",
        "measure_types": [
          "IMPORT_CONTROL"
        ],
        "records": [
          {
            "hs_code": "7208000000",
            "market": "EU",
            "origin_code": "KP",
            "origin_name": "KP",
            "origin_code_type": "country",
            "measure_type": "IMPORT_CONTROL",
            "rate_basis": "import_control",
            "duty_rate": null,
            "duty_amount": null,
            "rate_specific_unit": null,
            "valid_from": "2017-09-16",
            "valid_to": null,
            "source": "TARIC",
            "ingested_at": "2026-03-29T02:19:43.672418+00:00",
            "details": {
              "measure_type_text": "Import control on restricted goods and technologies",
              "measure_type_code": "711",
              "origin_text": "North Korea (Democratic People’s Republic of Korea)",
              "origin_code_raw": "KP",
              "legal_base": "Regulation 1548/17",
              "regulation": null,
              "additional_code": null,
              "order_no": null,
              "duty_text": "Cond:  Y cert: Y-959 (29):; Y (09):"
            }
          }
        ]
      },
      {
        "origin_code": "KR",
        "origin_name": "KR",
        "origin_code_type": "country",
        "measure_types": [
          "PREFERENTIAL",
          "TARIFF_QUOTA"
        ],
        "records": [
          {
            "hs_code": "7208510000",
            "market": "EU",
            "origin_code": "KR",
            "origin_name": "KR",
            "origin_code_type": "country",
            "measure_type": "TARIFF_QUOTA",
            "rate_basis": "tariff_quota",
            "duty_rate": 0,
            "duty_amount": null,
            "rate_specific_unit": null,
            "valid_from": "2025-04-01",
            "valid_to": "2026-06-30",
            "source": "TARIC",
            "ingested_at": "2026-03-29T02:19:46.886063+00:00",
            "details": {
              "measure_type_text": "Non preferential tariff quota",
              "measure_type_code": "122",
              "origin_text": "Korea, Republic of (South Korea)",
              "origin_code_raw": "KR",
              "legal_base": "Regulation 0159/19",
              "regulation": null,
              "additional_code": null,
              "order_no": "098427",
              "duty_text": "0.000 %"
            }
          },
          {
            "hs_code": "7200000000",
            "market": "EU",
            "origin_code": "KR",
            "origin_name": "KR",
            "origin_code_type": "country",
            "measure_type": "PREFERENTIAL",
            "rate_basis": "bilateral_preference",
            "duty_rate": 0,
            "duty_amount": null,
            "rate_specific_unit": null,
            "valid_from": "2011-07-01",
            "valid_to": null,
            "source": "TARIC",
            "ingested_at": "2026-03-29T02:19:41.750390+00:00",
            "details": {
              "measure_type_text": "Tariff preference",
              "measure_type_code": "142",
              "origin_text": "Korea, Republic of (South Korea)",
              "origin_code_raw": "KR",
              "legal_base": "Decision 0265/11",
              "regulation": null,
              "additional_code": null,
              "order_no": null,
              "duty_text": "0.000 %"
            }
          }
        ]
      },
      {
        "origin_code": "LB",
        "origin_name": "LB",
        "origin_code_type": "country",
        "measure_types": [
          "PREFERENTIAL"
        ],
        "records": [
          {
            "hs_code": "7200000000",
            "market": "EU",
            "origin_code": "LB",
            "origin_name": "LB",
            "origin_code_type": "country",
            "measure_type": "PREFERENTIAL",
            "rate_basis": "bilateral_preference",
            "duty_rate": 0,
            "duty_amount": null,
            "rate_specific_unit": null,
            "valid_from": "2006-04-01",
            "valid_to": null,
            "source": "TARIC",
            "ingested_at": "2026-03-29T02:19:41.740986+00:00",
            "details": {
              "measure_type_text": "Tariff preference",
              "measure_type_code": "142",
              "origin_text": "Lebanon",
              "origin_code_raw": "LB",
              "legal_base": "Decision 0356/06",
              "regulation": null,
              "additional_code": null,
              "order_no": null,
              "duty_text": "0.000 %"
            }
          }
        ]
      },
      {
        "origin_code": "MA",
        "origin_name": "MA",
        "origin_code_type": "country",
        "measure_types": [
          "PREFERENTIAL"
        ],
        "records": [
          {
            "hs_code": "7200000000",
            "market": "EU",
            "origin_code": "MA",
            "origin_name": "MA",
            "origin_code_type": "country",
            "measure_type": "PREFERENTIAL",
            "rate_basis": "bilateral_preference",
            "duty_rate": 0,
            "duty_amount": null,
            "rate_specific_unit": null,
            "valid_from": "2000-03-01",
            "valid_to": null,
            "source": "TARIC",
            "ingested_at": "2026-03-29T02:19:41.738251+00:00",
            "details": {
              "measure_type_text": "Tariff preference",
              "measure_type_code": "142",
              "origin_text": "Morocco",
              "origin_code_raw": "MA",
              "legal_base": "Decision 0204/00",
              "regulation": null,
              "additional_code": null,
              "order_no": null,
              "duty_text": "0.000 %"
            }
          }
        ]
      },
      {
        "origin_code": "PG",
        "origin_name": "PG",
        "origin_code_type": "country",
        "measure_types": [
          "PREFERENTIAL"
        ],
        "records": [
          {
            "hs_code": "7200000000",
            "market": "EU",
            "origin_code": "PG",
            "origin_name": "PG",
            "origin_code_type": "country",
            "measure_type": "PREFERENTIAL",
            "rate_basis": "bilateral_preference",
            "duty_rate": 0,
            "duty_amount": null,
            "rate_specific_unit": null,
            "valid_from": "2009-12-20",
            "valid_to": null,
            "source": "TARIC",
            "ingested_at": "2026-03-29T02:19:41.792251+00:00",
            "details": {
              "measure_type_text": "Tariff preference",
              "measure_type_code": "142",
              "origin_text": "Papua New Guinea",
              "origin_code_raw": "PG",
              "legal_base": "Decision 0729/09",
              "regulation": null,
              "additional_code": null,
              "order_no": null,
              "duty_text": "0.000 %"
            }
          }
        ]
      },
      {
        "origin_code": "PS",
        "origin_name": "PS",
        "origin_code_type": "country",
        "measure_types": [
          "PREFERENTIAL"
        ],
        "records": [
          {
            "hs_code": "7200000000",
            "market": "EU",
            "origin_code": "PS",
            "origin_name": "PS",
            "origin_code_type": "country",
            "measure_type": "PREFERENTIAL",
            "rate_basis": "bilateral_preference",
            "duty_rate": 0,
            "duty_amount": null,
            "rate_specific_unit": null,
            "valid_from": "2003-12-07",
            "valid_to": null,
            "source": "TARIC",
            "ingested_at": "2026-03-29T02:19:41.772224+00:00",
            "details": {
              "measure_type_text": "Tariff preference",
              "measure_type_code": "142",
              "origin_text": "Occupied palestinian Territory",
              "origin_code_raw": "PS",
              "legal_base": "Decision 0430/97",
              "regulation": null,
              "additional_code": null,
              "order_no": null,
              "duty_text": "0.000 %"
            }
          }
        ]
      },
      {
        "origin_code": "RU",
        "origin_name": "RU",
        "origin_code_type": "country",
        "measure_types": [
          "IMPORT_CONTROL"
        ],
        "records": [
          {
            "hs_code": "7208510000",
            "market": "EU",
            "origin_code": "RU",
            "origin_name": "RU",
            "origin_code_type": "country",
            "measure_type": "IMPORT_CONTROL",
            "rate_basis": "import_control",
            "duty_rate": null,
            "duty_amount": null,
            "rate_specific_unit": null,
            "valid_from": "2023-12-19",
            "valid_to": "2026-12-31",
            "source": "TARIC",
            "ingested_at": "2026-03-29T02:19:46.904006+00:00",
            "details": {
              "measure_type_text": "Import control",
              "measure_type_code": "763",
              "origin_text": "Russian Federation",
              "origin_code_raw": "RU",
              "legal_base": "Regulation 0833/14",
              "regulation": null,
              "additional_code": null,
              "order_no": null,
              "duty_text": "Cond:  Y cert: L-139 (29):; Y cert: L-143 (29):; Y cert: Y-859 (29):; Y (09):"
            }
          }
        ]
      },
      {
        "origin_code": "SB",
        "origin_name": "SB",
        "origin_code_type": "country",
        "measure_types": [
          "PREFERENTIAL"
        ],
        "records": [
          {
            "hs_code": "7200000000",
            "market": "EU",
            "origin_code": "SB",
            "origin_name": "SB",
            "origin_code_type": "country",
            "measure_type": "PREFERENTIAL",
            "rate_basis": "bilateral_preference",
            "duty_rate": 0,
            "duty_amount": null,
            "rate_specific_unit": null,
            "valid_from": "2020-05-17",
            "valid_to": null,
            "source": "TARIC",
            "ingested_at": "2026-03-29T02:19:41.789434+00:00",
            "details": {
              "measure_type_text": "Tariff preference",
              "measure_type_code": "142",
              "origin_text": "Solomon Islands",
              "origin_code_raw": "SB",
              "legal_base": "Decision 0729/09",
              "regulation": null,
              "additional_code": null,
              "order_no": null,
              "duty_text": "0.000 %"
            }
          }
        ]
      },
      {
        "origin_code": "TN",
        "origin_name": "TN",
        "origin_code_type": "country",
        "measure_types": [
          "PREFERENTIAL"
        ],
        "records": [
          {
            "hs_code": "7200000000",
            "market": "EU",
            "origin_code": "TN",
            "origin_name": "TN",
            "origin_code_type": "country",
            "measure_type": "PREFERENTIAL",
            "rate_basis": "bilateral_preference",
            "duty_rate": 0,
            "duty_amount": null,
            "rate_specific_unit": null,
            "valid_from": "1998-03-01",
            "valid_to": null,
            "source": "TARIC",
            "ingested_at": "2026-03-29T02:19:41.735464+00:00",
            "details": {
              "measure_type_text": "Tariff preference",
              "measure_type_code": "142",
              "origin_text": "Tunisia",
              "origin_code_raw": "TN",
              "legal_base": "Decision 0238/98",
              "regulation": null,
              "additional_code": null,
              "order_no": null,
              "duty_text": "0.000 %"
            }
          }
        ]
      },
      {
        "origin_code": "TR",
        "origin_name": "TR",
        "origin_code_type": "country",
        "measure_types": [
          "TARIFF_QUOTA"
        ],
        "records": [
          {
            "hs_code": "7208510000",
            "market": "EU",
            "origin_code": "TR",
            "origin_name": "TR",
            "origin_code_type": "country",
            "measure_type": "TARIFF_QUOTA",
            "rate_basis": "tariff_quota",
            "duty_rate": 0,
            "duty_amount": null,
            "rate_specific_unit": null,
            "valid_from": "2025-07-08",
            "valid_to": "2026-06-30",
            "source": "TARIC",
            "ingested_at": "2026-03-29T02:19:46.874650+00:00",
            "details": {
              "measure_type_text": "Non preferential tariff quota",
              "measure_type_code": "122",
              "origin_text": "Türkiye",
              "origin_code_raw": "TR",
              "legal_base": "Regulation 0159/19",
              "regulation": null,
              "additional_code": null,
              "order_no": "098418",
              "duty_text": "0.000 %"
            }
          }
        ]
      },
      {
        "origin_code": "UA",
        "origin_name": "UA",
        "origin_code_type": "country",
        "measure_types": [
          "IMPORT_CONTROL"
        ],
        "records": [
          {
            "hs_code": "7200000000",
            "market": "EU",
            "origin_code": "UA",
            "origin_name": "UA",
            "origin_code_type": "country",
            "measure_type": "IMPORT_CONTROL",
            "rate_basis": "import_control",
            "duty_rate": null,
            "duty_amount": null,
            "rate_specific_unit": null,
            "valid_from": "2025-01-01",
            "valid_to": null,
            "source": "TARIC",
            "ingested_at": "2026-03-29T02:19:41.732025+00:00",
            "details": {
              "measure_type_text": "Import control",
              "measure_type_code": "760",
              "origin_text": "Ukraine",
              "origin_code_raw": "UA",
              "legal_base": "Regulation 0692/14",
              "regulation": null,
              "additional_code": null,
              "order_no": null,
              "duty_text": "Cond:  Y cert: Y-997 (26):; Y cert: U-078 (26):; Y cert: U-079 (26):; Y cert: N-954 (26):; Y cert: U-045 (26):; Y (06):"
            }
          },
          {
            "hs_code": "7200000000",
            "market": "EU",
            "origin_code": "UA",
            "origin_name": "UA",
            "origin_code_type": "country",
            "measure_type": "IMPORT_CONTROL",
            "rate_basis": "import_control",
            "duty_rate": null,
            "duty_amount": null,
            "rate_specific_unit": null,
            "valid_from": "2025-01-01",
            "valid_to": null,
            "source": "TARIC",
            "ingested_at": "2026-03-29T02:19:41.725202+00:00",
            "details": {
              "measure_type_text": "Import control",
              "measure_type_code": "762",
              "origin_text": "Ukraine",
              "origin_code_raw": "UA",
              "legal_base": "Regulation 0263/22",
              "regulation": null,
              "additional_code": null,
              "order_no": null,
              "duty_text": "Cond:  Y cert: Y-984 (29):; Y cert: N-954 (29):; Y cert: U-045 (29):; Y cert: U-078 (29):; Y cert: U-079 (29):; Y (09):"
            }
          }
        ]
      },
      {
        "origin_code": "WS",
        "origin_name": "WS",
        "origin_code_type": "country",
        "measure_types": [
          "PREFERENTIAL"
        ],
        "records": [
          {
            "hs_code": "7200000000",
            "market": "EU",
            "origin_code": "WS",
            "origin_name": "WS",
            "origin_code_type": "country",
            "measure_type": "PREFERENTIAL",
            "rate_basis": "bilateral_preference",
            "duty_rate": 0,
            "duty_amount": null,
            "rate_specific_unit": null,
            "valid_from": "2018-12-31",
            "valid_to": null,
            "source": "TARIC",
            "ingested_at": "2026-03-29T02:19:41.802409+00:00",
            "details": {
              "measure_type_text": "Tariff preference",
              "measure_type_code": "142",
              "origin_text": "Samoa",
              "origin_code_raw": "WS",
              "legal_base": "Decision 0729/09",
              "regulation": null,
              "additional_code": null,
              "order_no": null,
              "duty_text": "0.000 %"
            }
          }
        ]
      },
      {
        "origin_code": "XC",
        "origin_name": "XC",
        "origin_code_type": "country",
        "measure_types": [
          "PREFERENTIAL"
        ],
        "records": [
          {
            "hs_code": "7200000000",
            "market": "EU",
            "origin_code": "XC",
            "origin_name": "XC",
            "origin_code_type": "country",
            "measure_type": "PREFERENTIAL",
            "rate_basis": "bilateral_preference",
            "duty_rate": 0,
            "duty_amount": null,
            "rate_specific_unit": null,
            "valid_from": "2003-12-07",
            "valid_to": null,
            "source": "TARIC",
            "ingested_at": "2026-03-29T02:19:41.765565+00:00",
            "details": {
              "measure_type_text": "Tariff preference",
              "measure_type_code": "142",
              "origin_text": "Ceuta",
              "origin_code_raw": "XC",
              "legal_base": "Accession act 0001/85",
              "regulation": null,
              "additional_code": null,
              "order_no": null,
              "duty_text": "0.000 %"
            }
          }
        ]
      },
      {
        "origin_code": "XL",
        "origin_name": "XL",
        "origin_code_type": "country",
        "measure_types": [
          "PREFERENTIAL"
        ],
        "records": [
          {
            "hs_code": "7200000000",
            "market": "EU",
            "origin_code": "XL",
            "origin_name": "XL",
            "origin_code_type": "country",
            "measure_type": "PREFERENTIAL",
            "rate_basis": "bilateral_preference",
            "duty_rate": 0,
            "duty_amount": null,
            "rate_specific_unit": null,
            "valid_from": "2003-12-07",
            "valid_to": null,
            "source": "TARIC",
            "ingested_at": "2026-03-29T02:19:41.769003+00:00",
            "details": {
              "measure_type_text": "Tariff preference",
              "measure_type_code": "142",
              "origin_text": "Melilla",
              "origin_code_raw": "XL",
              "legal_base": "Accession act 0001/85",
              "regulation": null,
              "additional_code": null,
              "order_no": null,
              "duty_text": "0.000 %"
            }
          }
        ]
      }
    ],
    "records": [],
    "measures_by_type": {
      "IMPORT_CONTROL": [
        {
          "hs_code": "7208510000",
          "market": "EU",
          "origin_code": "1008",
          "origin_name": "All third countries",
          "origin_code_type": "group_numeric",
          "measure_type": "IMPORT_CONTROL",
          "rate_basis": "import_control",
          "duty_rate": null,
          "duty_amount": null,
          "rate_specific_unit": null,
          "valid_from": "2023-12-19",
          "valid_to": "2026-12-31",
          "source": "TARIC",
          "ingested_at": "2026-03-29T02:19:46.912261+00:00",
          "details": {
            "measure_type_text": "Import control",
            "measure_type_code": "763",
            "origin_text": "All third countries",
            "origin_code_raw": "1008",
            "legal_base": "Regulation 0833/14",
            "regulation": null,
            "additional_code": null,
            "order_no": null,
            "duty_text": "Cond:  Y cert: L-139 (29):; Y cert: Y-824 (29):; Y cert: Y-878 (29):; Y cert: Y-859 (29):; Y cert: L-143 (29):; Y (09):"
          }
        },
        {
          "hs_code": "7208510000",
          "market": "EU",
          "origin_code": "RU",
          "origin_name": "RU",
          "origin_code_type": "country",
          "measure_type": "IMPORT_CONTROL",
          "rate_basis": "import_control",
          "duty_rate": null,
          "duty_amount": null,
          "rate_specific_unit": null,
          "valid_from": "2023-12-19",
          "valid_to": "2026-12-31",
          "source": "TARIC",
          "ingested_at": "2026-03-29T02:19:46.904006+00:00",
          "details": {
            "measure_type_text": "Import control",
            "measure_type_code": "763",
            "origin_text": "Russian Federation",
            "origin_code_raw": "RU",
            "legal_base": "Regulation 0833/14",
            "regulation": null,
            "additional_code": null,
            "order_no": null,
            "duty_text": "Cond:  Y cert: L-139 (29):; Y cert: L-143 (29):; Y cert: Y-859 (29):; Y (09):"
          }
        },
        {
          "hs_code": "7208000000",
          "market": "EU",
          "origin_code": "KP",
          "origin_name": "KP",
          "origin_code_type": "country",
          "measure_type": "IMPORT_CONTROL",
          "rate_basis": "import_control",
          "duty_rate": null,
          "duty_amount": null,
          "rate_specific_unit": null,
          "valid_from": "2017-09-16",
          "valid_to": null,
          "source": "TARIC",
          "ingested_at": "2026-03-29T02:19:43.672418+00:00",
          "details": {
            "measure_type_text": "Import control on restricted goods and technologies",
            "measure_type_code": "711",
            "origin_text": "North Korea (Democratic People’s Republic of Korea)",
            "origin_code_raw": "KP",
            "legal_base": "Regulation 1548/17",
            "regulation": null,
            "additional_code": null,
            "order_no": null,
            "duty_text": "Cond:  Y cert: Y-959 (29):; Y (09):"
          }
        },
        {
          "hs_code": "7200000000",
          "market": "EU",
          "origin_code": "UA",
          "origin_name": "UA",
          "origin_code_type": "country",
          "measure_type": "IMPORT_CONTROL",
          "rate_basis": "import_control",
          "duty_rate": null,
          "duty_amount": null,
          "rate_specific_unit": null,
          "valid_from": "2025-01-01",
          "valid_to": null,
          "source": "TARIC",
          "ingested_at": "2026-03-29T02:19:41.732025+00:00",
          "details": {
            "measure_type_text": "Import control",
            "measure_type_code": "760",
            "origin_text": "Ukraine",
            "origin_code_raw": "UA",
            "legal_base": "Regulation 0692/14",
            "regulation": null,
            "additional_code": null,
            "order_no": null,
            "duty_text": "Cond:  Y cert: Y-997 (26):; Y cert: U-078 (26):; Y cert: U-079 (26):; Y cert: N-954 (26):; Y cert: U-045 (26):; Y (06):"
          }
        },
        {
          "hs_code": "7200000000",
          "market": "EU",
          "origin_code": "UA",
          "origin_name": "UA",
          "origin_code_type": "country",
          "measure_type": "IMPORT_CONTROL",
          "rate_basis": "import_control",
          "duty_rate": null,
          "duty_amount": null,
          "rate_specific_unit": null,
          "valid_from": "2025-01-01",
          "valid_to": null,
          "source": "TARIC",
          "ingested_at": "2026-03-29T02:19:41.725202+00:00",
          "details": {
            "measure_type_text": "Import control",
            "measure_type_code": "762",
            "origin_text": "Ukraine",
            "origin_code_raw": "UA",
            "legal_base": "Regulation 0263/22",
            "regulation": null,
            "additional_code": null,
            "order_no": null,
            "duty_text": "Cond:  Y cert: Y-984 (29):; Y cert: N-954 (29):; Y cert: U-045 (29):; Y cert: U-078 (29):; Y cert: U-079 (29):; Y (09):"
          }
        }
      ],
      "SAFEGUARD": [
        {
          "hs_code": "7208510000",
          "market": "EU",
          "origin_code": "5005",
          "origin_name": "5005",
          "origin_code_type": "safeguard",
          "measure_type": "SAFEGUARD",
          "rate_basis": "safeguard",
          "duty_rate": 25,
          "duty_amount": null,
          "rate_specific_unit": null,
          "valid_from": "2025-04-01",
          "valid_to": "2026-06-30",
          "source": "TARIC",
          "ingested_at": "2026-03-29T02:19:46.897504+00:00",
          "details": {
            "measure_type_text": "Additional duties (safeguard)",
            "measure_type_code": "696",
            "origin_text": "Countries subject to safeguard measures",
            "origin_code_raw": "5005",
            "legal_base": "Regulation 0159/19",
            "regulation": null,
            "additional_code": null,
            "order_no": null,
            "duty_text": "25.000 %"
          }
        }
      ],
      "TARIFF_QUOTA": [
        {
          "hs_code": "7208510000",
          "market": "EU",
          "origin_code": "5005",
          "origin_name": "5005",
          "origin_code_type": "safeguard",
          "measure_type": "TARIFF_QUOTA",
          "rate_basis": "tariff_quota",
          "duty_rate": 0,
          "duty_amount": null,
          "rate_specific_unit": null,
          "valid_from": "2025-07-08",
          "valid_to": "2026-03-31",
          "source": "TARIC",
          "ingested_at": "2026-03-29T02:19:46.889824+00:00",
          "details": {
            "measure_type_text": "Non preferential tariff quota",
            "measure_type_code": "122",
            "origin_text": "Countries subject to safeguard measures",
            "origin_code_raw": "5005",
            "legal_base": "Regulation 0159/19",
            "regulation": null,
            "additional_code": null,
            "order_no": "098617",
            "duty_text": "0.000 %"
          }
        },
        {
          "hs_code": "7208510000",
          "market": "EU",
          "origin_code": "KR",
          "origin_name": "KR",
          "origin_code_type": "country",
          "measure_type": "TARIFF_QUOTA",
          "rate_basis": "tariff_quota",
          "duty_rate": 0,
          "duty_amount": null,
          "rate_specific_unit": null,
          "valid_from": "2025-04-01",
          "valid_to": "2026-06-30",
          "source": "TARIC",
          "ingested_at": "2026-03-29T02:19:46.886063+00:00",
          "details": {
            "measure_type_text": "Non preferential tariff quota",
            "measure_type_code": "122",
            "origin_text": "Korea, Republic of (South Korea)",
            "origin_code_raw": "KR",
            "legal_base": "Regulation 0159/19",
            "regulation": null,
            "additional_code": null,
            "order_no": "098427",
            "duty_text": "0.000 %"
          }
        },
        {
          "hs_code": "7208510000",
          "market": "EU",
          "origin_code": "ID",
          "origin_name": "ID",
          "origin_code_type": "country",
          "measure_type": "TARIFF_QUOTA",
          "rate_basis": "tariff_quota",
          "duty_rate": 0,
          "duty_amount": null,
          "rate_specific_unit": null,
          "valid_from": "2025-04-01",
          "valid_to": "2026-06-30",
          "source": "TARIC",
          "ingested_at": "2026-03-29T02:19:46.881990+00:00",
          "details": {
            "measure_type_text": "Non preferential tariff quota",
            "measure_type_code": "122",
            "origin_text": "Indonesia",
            "origin_code_raw": "ID",
            "legal_base": "Regulation 0159/19",
            "regulation": null,
            "additional_code": null,
            "order_no": "098426",
            "duty_text": "0.000 %"
          }
        },
        {
          "hs_code": "7208510000",
          "market": "EU",
          "origin_code": "IN",
          "origin_name": "IN",
          "origin_code_type": "country",
          "measure_type": "TARIFF_QUOTA",
          "rate_basis": "tariff_quota",
          "duty_rate": 0,
          "duty_amount": null,
          "rate_specific_unit": null,
          "valid_from": "2025-04-01",
          "valid_to": "2026-06-30",
          "source": "TARIC",
          "ingested_at": "2026-03-29T02:19:46.878214+00:00",
          "details": {
            "measure_type_text": "Non preferential tariff quota",
            "measure_type_code": "122",
            "origin_text": "India",
            "origin_code_raw": "IN",
            "legal_base": "Regulation 0159/19",
            "regulation": null,
            "additional_code": null,
            "order_no": "098425",
            "duty_text": "0.000 %"
          }
        },
        {
          "hs_code": "7208510000",
          "market": "EU",
          "origin_code": "TR",
          "origin_name": "TR",
          "origin_code_type": "country",
          "measure_type": "TARIFF_QUOTA",
          "rate_basis": "tariff_quota",
          "duty_rate": 0,
          "duty_amount": null,
          "rate_specific_unit": null,
          "valid_from": "2025-07-08",
          "valid_to": "2026-06-30",
          "source": "TARIC",
          "ingested_at": "2026-03-29T02:19:46.874650+00:00",
          "details": {
            "measure_type_text": "Non preferential tariff quota",
            "measure_type_code": "122",
            "origin_text": "Türkiye",
            "origin_code_raw": "TR",
            "legal_base": "Regulation 0159/19",
            "regulation": null,
            "additional_code": null,
            "order_no": "098418",
            "duty_text": "0.000 %"
          }
        }
      ],
      "SUSPENSION": [
        {
          "hs_code": "7208000000",
          "market": "EU",
          "origin_code": "1011",
          "origin_name": "ERGA OMNES",
          "origin_code_type": "erga_omnes",
          "measure_type": "SUSPENSION",
          "rate_basis": "MFN",
          "duty_rate": 0,
          "duty_amount": null,
          "rate_specific_unit": null,
          "valid_from": "2016-07-01",
          "valid_to": null,
          "source": "TARIC",
          "ingested_at": "2026-03-29T02:19:43.668137+00:00",
          "details": {
            "measure_type_text": "Suspension - goods for certain categories of ships, boats and other vessels and for drilling or production platforms",
            "measure_type_code": "117",
            "origin_text": "ERGA OMNES",
            "origin_code_raw": "1011",
            "legal_base": "Regulation 2658/87",
            "regulation": null,
            "additional_code": null,
            "order_no": null,
            "duty_text": "0.000 %"
          }
        }
      ],
      "MFN": [
        {
          "hs_code": "7208000000",
          "market": "EU",
          "origin_code": "1011",
          "origin_name": "ERGA OMNES",
          "origin_code_type": "erga_omnes",
          "measure_type": "MFN",
          "rate_basis": "MFN",
          "duty_rate": 0,
          "duty_amount": null,
          "rate_specific_unit": null,
          "valid_from": "2005-01-01",
          "valid_to": null,
          "source": "TARIC",
          "ingested_at": "2026-03-29T02:19:43.664808+00:00",
          "details": {
            "measure_type_text": "Third country duty",
            "measure_type_code": "103",
            "origin_text": "ERGA OMNES",
            "origin_code_raw": "1011",
            "legal_base": "Regulation 1789/03",
            "regulation": null,
            "additional_code": null,
            "order_no": null,
            "duty_text": "0.000 %"
          }
        }
      ],
      "PREFERENTIAL": [
        {
          "hs_code": "7200000000",
          "market": "EU",
          "origin_code": "WS",
          "origin_name": "WS",
          "origin_code_type": "country",
          "measure_type": "PREFERENTIAL",
          "rate_basis": "bilateral_preference",
          "duty_rate": 0,
          "duty_amount": null,
          "rate_specific_unit": null,
          "valid_from": "2018-12-31",
          "valid_to": null,
          "source": "TARIC",
          "ingested_at": "2026-03-29T02:19:41.802409+00:00",
          "details": {
            "measure_type_text": "Tariff preference",
            "measure_type_code": "142",
            "origin_text": "Samoa",
            "origin_code_raw": "WS",
            "legal_base": "Decision 0729/09",
            "regulation": null,
            "additional_code": null,
            "order_no": null,
            "duty_text": "0.000 %"
          }
        },
        {
          "hs_code": "7200000000",
          "market": "EU",
          "origin_code": "1033",
          "origin_name": "1033",
          "origin_code_type": "group_numeric",
          "measure_type": "PREFERENTIAL",
          "rate_basis": "group_preference",
          "duty_rate": 0,
          "duty_amount": null,
          "rate_specific_unit": null,
          "valid_from": "2008-12-29",
          "valid_to": null,
          "source": "TARIC",
          "ingested_at": "2026-03-29T02:19:41.799604+00:00",
          "details": {
            "measure_type_text": "Tariff preference",
            "measure_type_code": "142",
            "origin_text": "CARIFORUM",
            "origin_code_raw": "1033",
            "legal_base": "Decision 0805/08",
            "regulation": null,
            "additional_code": null,
            "order_no": null,
            "duty_text": "0.000 %"
          }
        },
        {
          "hs_code": "7200000000",
          "market": "EU",
          "origin_code": "FJ",
          "origin_name": "FJ",
          "origin_code_type": "country",
          "measure_type": "PREFERENTIAL",
          "rate_basis": "bilateral_preference",
          "duty_rate": 0,
          "duty_amount": null,
          "rate_specific_unit": null,
          "valid_from": "2014-07-28",
          "valid_to": null,
          "source": "TARIC",
          "ingested_at": "2026-03-29T02:19:41.795223+00:00",
          "details": {
            "measure_type_text": "Tariff preference",
            "measure_type_code": "142",
            "origin_text": "Fiji",
            "origin_code_raw": "FJ",
            "legal_base": "Decision 0729/09",
            "regulation": null,
            "additional_code": null,
            "order_no": null,
            "duty_text": "0.000 %"
          }
        },
        {
          "hs_code": "7200000000",
          "market": "EU",
          "origin_code": "PG",
          "origin_name": "PG",
          "origin_code_type": "country",
          "measure_type": "PREFERENTIAL",
          "rate_basis": "bilateral_preference",
          "duty_rate": 0,
          "duty_amount": null,
          "rate_specific_unit": null,
          "valid_from": "2009-12-20",
          "valid_to": null,
          "source": "TARIC",
          "ingested_at": "2026-03-29T02:19:41.792251+00:00",
          "details": {
            "measure_type_text": "Tariff preference",
            "measure_type_code": "142",
            "origin_text": "Papua New Guinea",
            "origin_code_raw": "PG",
            "legal_base": "Decision 0729/09",
            "regulation": null,
            "additional_code": null,
            "order_no": null,
            "duty_text": "0.000 %"
          }
        },
        {
          "hs_code": "7200000000",
          "market": "EU",
          "origin_code": "SB",
          "origin_name": "SB",
          "origin_code_type": "country",
          "measure_type": "PREFERENTIAL",
          "rate_basis": "bilateral_preference",
          "duty_rate": 0,
          "duty_amount": null,
          "rate_specific_unit": null,
          "valid_from": "2020-05-17",
          "valid_to": null,
          "source": "TARIC",
          "ingested_at": "2026-03-29T02:19:41.789434+00:00",
          "details": {
            "measure_type_text": "Tariff preference",
            "measure_type_code": "142",
            "origin_text": "Solomon Islands",
            "origin_code_raw": "SB",
            "legal_base": "Decision 0729/09",
            "regulation": null,
            "additional_code": null,
            "order_no": null,
            "duty_text": "0.000 %"
          }
        },
        {
          "hs_code": "7200000000",
          "market": "EU",
          "origin_code": "IL",
          "origin_name": "IL",
          "origin_code_type": "country",
          "measure_type": "PREFERENTIAL",
          "rate_basis": "bilateral_preference",
          "duty_rate": 0,
          "duty_amount": null,
          "rate_specific_unit": null,
          "valid_from": "2023-05-16",
          "valid_to": null,
          "source": "TARIC",
          "ingested_at": "2026-03-29T02:19:41.786262+00:00",
          "details": {
            "measure_type_text": "Tariff preference",
            "measure_type_code": "142",
            "origin_text": "Israel",
            "origin_code_raw": "IL",
            "legal_base": "Decision 0855/09",
            "regulation": null,
            "additional_code": null,
            "order_no": null,
            "duty_text": "0.000 %"
          }
        },
        {
          "hs_code": "7200000000",
          "market": "EU",
          "origin_code": "GH",
          "origin_name": "GH",
          "origin_code_type": "country",
          "measure_type": "PREFERENTIAL",
          "rate_basis": "bilateral_preference",
          "duty_rate": 0,
          "duty_amount": null,
          "rate_specific_unit": null,
          "valid_from": "2016-12-15",
          "valid_to": null,
          "source": "TARIC",
          "ingested_at": "2026-03-29T02:19:41.783366+00:00",
          "details": {
            "measure_type_text": "Tariff preference",
            "measure_type_code": "142",
            "origin_text": "Ghana",
            "origin_code_raw": "GH",
            "legal_base": "Decision 1850/16",
            "regulation": null,
            "additional_code": null,
            "order_no": null,
            "duty_text": "0.000 %"
          }
        },
        {
          "hs_code": "7200000000",
          "market": "EU",
          "origin_code": "1034",
          "origin_name": "1034",
          "origin_code_type": "group_numeric",
          "measure_type": "PREFERENTIAL",
          "rate_basis": "group_preference",
          "duty_rate": 0,
          "duty_amount": null,
          "rate_specific_unit": null,
          "valid_from": "2012-05-14",
          "valid_to": null,
          "source": "TARIC",
          "ingested_at": "2026-03-29T02:19:41.780391+00:00",
          "details": {
            "measure_type_text": "Tariff preference",
            "measure_type_code": "142",
            "origin_text": "Eastern and Southern Africa States",
            "origin_code_raw": "1034",
            "legal_base": "Decision 0196/12",
            "regulation": null,
            "additional_code": null,
            "order_no": null,
            "duty_text": "0.000 %"
          }
        },
        {
          "hs_code": "7200000000",
          "market": "EU",
          "origin_code": "1035",
          "origin_name": "1035",
          "origin_code_type": "group_numeric",
          "measure_type": "PREFERENTIAL",
          "rate_basis": "group_preference",
          "duty_rate": 0,
          "duty_amount": null,
          "rate_specific_unit": null,
          "valid_from": "2016-10-10",
          "valid_to": null,
          "source": "TARIC",
          "ingested_at": "2026-03-29T02:19:41.776204+00:00",
          "details": {
            "measure_type_text": "Tariff preference",
            "measure_type_code": "142",
            "origin_text": "SADC EPA",
            "origin_code_raw": "1035",
            "legal_base": "Decision 1623/16",
            "regulation": null,
            "additional_code": null,
            "order_no": null,
            "duty_text": "0.000 %"
          }
        },
        {
          "hs_code": "7200000000",
          "market": "EU",
          "origin_code": "PS",
          "origin_name": "PS",
          "origin_code_type": "country",
          "measure_type": "PREFERENTIAL",
          "rate_basis": "bilateral_preference",
          "duty_rate": 0,
          "duty_amount": null,
          "rate_specific_unit": null,
          "valid_from": "2003-12-07",
          "valid_to": null,
          "source": "TARIC",
          "ingested_at": "2026-03-29T02:19:41.772224+00:00",
          "details": {
            "measure_type_text": "Tariff preference",
            "measure_type_code": "142",
            "origin_text": "Occupied palestinian Territory",
            "origin_code_raw": "PS",
            "legal_base": "Decision 0430/97",
            "regulation": null,
            "additional_code": null,
            "order_no": null,
            "duty_text": "0.000 %"
          }
        },
        {
          "hs_code": "7200000000",
          "market": "EU",
          "origin_code": "XL",
          "origin_name": "XL",
          "origin_code_type": "country",
          "measure_type": "PREFERENTIAL",
          "rate_basis": "bilateral_preference",
          "duty_rate": 0,
          "duty_amount": null,
          "rate_specific_unit": null,
          "valid_from": "2003-12-07",
          "valid_to": null,
          "source": "TARIC",
          "ingested_at": "2026-03-29T02:19:41.769003+00:00",
          "details": {
            "measure_type_text": "Tariff preference",
            "measure_type_code": "142",
            "origin_text": "Melilla",
            "origin_code_raw": "XL",
            "legal_base": "Accession act 0001/85",
            "regulation": null,
            "additional_code": null,
            "order_no": null,
            "duty_text": "0.000 %"
          }
        },
        {
          "hs_code": "7200000000",
          "market": "EU",
          "origin_code": "XC",
          "origin_name": "XC",
          "origin_code_type": "country",
          "measure_type": "PREFERENTIAL",
          "rate_basis": "bilateral_preference",
          "duty_rate": 0,
          "duty_amount": null,
          "rate_specific_unit": null,
          "valid_from": "2003-12-07",
          "valid_to": null,
          "source": "TARIC",
          "ingested_at": "2026-03-29T02:19:41.765565+00:00",
          "details": {
            "measure_type_text": "Tariff preference",
            "measure_type_code": "142",
            "origin_text": "Ceuta",
            "origin_code_raw": "XC",
            "legal_base": "Accession act 0001/85",
            "regulation": null,
            "additional_code": null,
            "order_no": null,
            "duty_text": "0.000 %"
          }
        },
        {
          "hs_code": "7200000000",
          "market": "EU",
          "origin_code": "CM",
          "origin_name": "CM",
          "origin_code_type": "country",
          "measure_type": "PREFERENTIAL",
          "rate_basis": "bilateral_preference",
          "duty_rate": 0,
          "duty_amount": null,
          "rate_specific_unit": null,
          "valid_from": "2014-08-04",
          "valid_to": null,
          "source": "TARIC",
          "ingested_at": "2026-03-29T02:19:41.762201+00:00",
          "details": {
            "measure_type_text": "Tariff preference",
            "measure_type_code": "142",
            "origin_text": "Cameroon",
            "origin_code_raw": "CM",
            "legal_base": "Decision 0152/09",
            "regulation": null,
            "additional_code": null,
            "order_no": null,
            "duty_text": "0.000 %"
          }
        },
        {
          "hs_code": "7200000000",
          "market": "EU",
          "origin_code": "2000",
          "origin_name": "2000",
          "origin_code_type": "group_numeric",
          "measure_type": "PREFERENTIAL",
          "rate_basis": "group_preference",
          "duty_rate": 0,
          "duty_amount": null,
          "rate_specific_unit": null,
          "valid_from": "2025-10-03",
          "valid_to": null,
          "source": "TARIC",
          "ingested_at": "2026-03-29T02:19:41.759381+00:00",
          "details": {
            "measure_type_text": "Tariff preference",
            "measure_type_code": "142",
            "origin_text": "Preferential origin in accordance with the Agreement in the form of an Exchange of Letters between the European Union and the Kingdom of Morocco on the amendment of Protocols 1 and 4 to the Euro-Mediterranean Agreement establishing an association between the European Communities and their Member States, of the one part, and the Kingdom of Morocco, of the other part.",
            "origin_code_raw": "2000",
            "legal_base": "Decision 2022/25",
            "regulation": null,
            "additional_code": null,
            "order_no": null,
            "duty_text": "0.000 %"
          }
        },
        {
          "hs_code": "7200000000",
          "market": "EU",
          "origin_code": "CI",
          "origin_name": "CI",
          "origin_code_type": "country",
          "measure_type": "PREFERENTIAL",
          "rate_basis": "bilateral_preference",
          "duty_rate": 0,
          "duty_amount": null,
          "rate_specific_unit": null,
          "valid_from": "2019-12-02",
          "valid_to": null,
          "source": "TARIC",
          "ingested_at": "2026-03-29T02:19:41.755777+00:00",
          "details": {
            "measure_type_text": "Tariff preference",
            "measure_type_code": "142",
            "origin_text": "Ivory Coast",
            "origin_code_raw": "CI",
            "legal_base": "Decision 0156/09",
            "regulation": null,
            "additional_code": null,
            "order_no": null,
            "duty_text": "0.000 %"
          }
        },
        {
          "hs_code": "7200000000",
          "market": "EU",
          "origin_code": "KE",
          "origin_name": "KE",
          "origin_code_type": "country",
          "measure_type": "PREFERENTIAL",
          "rate_basis": "bilateral_preference",
          "duty_rate": 0,
          "duty_amount": null,
          "rate_specific_unit": null,
          "valid_from": "2024-07-01",
          "valid_to": null,
          "source": "TARIC",
          "ingested_at": "2026-03-29T02:19:41.753072+00:00",
          "details": {
            "measure_type_text": "Tariff preference",
            "measure_type_code": "142",
            "origin_text": "Kenya",
            "origin_code_raw": "KE",
            "legal_base": "Decision 1647/24",
            "regulation": null,
            "additional_code": null,
            "order_no": null,
            "duty_text": "0.000 %"
          }
        },
        {
          "hs_code": "7200000000",
          "market": "EU",
          "origin_code": "KR",
          "origin_name": "KR",
          "origin_code_type": "country",
          "measure_type": "PREFERENTIAL",
          "rate_basis": "bilateral_preference",
          "duty_rate": 0,
          "duty_amount": null,
          "rate_specific_unit": null,
          "valid_from": "2011-07-01",
          "valid_to": null,
          "source": "TARIC",
          "ingested_at": "2026-03-29T02:19:41.750390+00:00",
          "details": {
            "measure_type_text": "Tariff preference",
            "measure_type_code": "142",
            "origin_text": "Korea, Republic of (South Korea)",
            "origin_code_raw": "KR",
            "legal_base": "Decision 0265/11",
            "regulation": null,
            "additional_code": null,
            "order_no": null,
            "duty_text": "0.000 %"
          }
        },
        {
          "hs_code": "7200000000",
          "market": "EU",
          "origin_code": "EG",
          "origin_name": "EG",
          "origin_code_type": "country",
          "measure_type": "PREFERENTIAL",
          "rate_basis": "bilateral_preference",
          "duty_rate": 0,
          "duty_amount": null,
          "rate_specific_unit": null,
          "valid_from": "2004-06-01",
          "valid_to": null,
          "source": "TARIC",
          "ingested_at": "2026-03-29T02:19:41.747214+00:00",
          "details": {
            "measure_type_text": "Tariff preference",
            "measure_type_code": "142",
            "origin_text": "Egypt",
            "origin_code_raw": "EG",
            "legal_base": "Decision 0635/04",
            "regulation": null,
            "additional_code": null,
            "order_no": null,
            "duty_text": "0.000 %"
          }
        },
        {
          "hs_code": "7200000000",
          "market": "EU",
          "origin_code": "JO",
          "origin_name": "JO",
          "origin_code_type": "country",
          "measure_type": "PREFERENTIAL",
          "rate_basis": "bilateral_preference",
          "duty_rate": 0,
          "duty_amount": null,
          "rate_specific_unit": null,
          "valid_from": "2002-05-01",
          "valid_to": null,
          "source": "TARIC",
          "ingested_at": "2026-03-29T02:19:41.743699+00:00",
          "details": {
            "measure_type_text": "Tariff preference",
            "measure_type_code": "142",
            "origin_text": "Jordan",
            "origin_code_raw": "JO",
            "legal_base": "Decision 0357/02",
            "regulation": null,
            "additional_code": null,
            "order_no": null,
            "duty_text": "0.000 %"
          }
        },
        {
          "hs_code": "7200000000",
          "market": "EU",
          "origin_code": "LB",
          "origin_name": "LB",
          "origin_code_type": "country",
          "measure_type": "PREFERENTIAL",
          "rate_basis": "bilateral_preference",
          "duty_rate": 0,
          "duty_amount": null,
          "rate_specific_unit": null,
          "valid_from": "2006-04-01",
          "valid_to": null,
          "source": "TARIC",
          "ingested_at": "2026-03-29T02:19:41.740986+00:00",
          "details": {
            "measure_type_text": "Tariff preference",
            "measure_type_code": "142",
            "origin_text": "Lebanon",
            "origin_code_raw": "LB",
            "legal_base": "Decision 0356/06",
            "regulation": null,
            "additional_code": null,
            "order_no": null,
            "duty_text": "0.000 %"
          }
        },
        {
          "hs_code": "7200000000",
          "market": "EU",
          "origin_code": "MA",
          "origin_name": "MA",
          "origin_code_type": "country",
          "measure_type": "PREFERENTIAL",
          "rate_basis": "bilateral_preference",
          "duty_rate": 0,
          "duty_amount": null,
          "rate_specific_unit": null,
          "valid_from": "2000-03-01",
          "valid_to": null,
          "source": "TARIC",
          "ingested_at": "2026-03-29T02:19:41.738251+00:00",
          "details": {
            "measure_type_text": "Tariff preference",
            "measure_type_code": "142",
            "origin_text": "Morocco",
            "origin_code_raw": "MA",
            "legal_base": "Decision 0204/00",
            "regulation": null,
            "additional_code": null,
            "order_no": null,
            "duty_text": "0.000 %"
          }
        },
        {
          "hs_code": "7200000000",
          "market": "EU",
          "origin_code": "TN",
          "origin_name": "TN",
          "origin_code_type": "country",
          "measure_type": "PREFERENTIAL",
          "rate_basis": "bilateral_preference",
          "duty_rate": 0,
          "duty_amount": null,
          "rate_specific_unit": null,
          "valid_from": "1998-03-01",
          "valid_to": null,
          "source": "TARIC",
          "ingested_at": "2026-03-29T02:19:41.735464+00:00",
          "details": {
            "measure_type_text": "Tariff preference",
            "measure_type_code": "142",
            "origin_text": "Tunisia",
            "origin_code_raw": "TN",
            "legal_base": "Decision 0238/98",
            "regulation": null,
            "additional_code": null,
            "order_no": null,
            "duty_text": "0.000 %"
          }
        },
        {
          "hs_code": "7200000000",
          "market": "EU",
          "origin_code": "GB",
          "origin_name": "GB",
          "origin_code_type": "country",
          "measure_type": "PREFERENTIAL",
          "rate_basis": "bilateral_preference",
          "duty_rate": 0,
          "duty_amount": null,
          "rate_specific_unit": null,
          "valid_from": "2021-01-01",
          "valid_to": null,
          "source": "TARIC",
          "ingested_at": "2026-03-29T02:19:41.718056+00:00",
          "details": {
            "measure_type_text": "Tariff preference",
            "measure_type_code": "142",
            "origin_text": "United Kingdom",
            "origin_code_raw": "GB",
            "legal_base": "Decision 2253/20",
            "regulation": null,
            "additional_code": null,
            "order_no": null,
            "duty_text": "0.000 %"
          }
        },
        {
          "hs_code": "7200000000",
          "market": "EU",
          "origin_code": "2005",
          "origin_name": "2005",
          "origin_code_type": "group_numeric",
          "measure_type": "PREFERENTIAL",
          "rate_basis": "group_preference",
          "duty_rate": 0,
          "duty_amount": null,
          "rate_specific_unit": null,
          "valid_from": "2014-01-01",
          "valid_to": null,
          "source": "TARIC",
          "ingested_at": "2026-03-29T02:19:41.715058+00:00",
          "details": {
            "measure_type_text": "Tariff preference",
            "measure_type_code": "142",
            "origin_text": "GSP-EBA (Special arrangement for the least-developed countries - Everything But Arms)",
            "origin_code_raw": "2005",
            "legal_base": "Regulation 0978/12",
            "regulation": null,
            "additional_code": null,
            "order_no": null,
            "duty_text": "0.000 %"
          }
        }
      ]
    },
    "certificate_codes": [
      "L-139",
      "L-143",
      "N-954",
      "U-045",
      "U-078",
      "U-079",
      "Y-824",
      "Y-859",
      "Y-878",
      "Y-959",
      "Y-984",
      "Y-997"
    ],
    "certificate_details": {
      "Y-984": "Unknown — code Y-984",
      "N-954": "Unknown — code N-954",
      "U-045": "Unknown — code U-045",
      "U-078": "Unknown — code U-078",
      "U-079": "Unknown — code U-079",
      "Y-997": "Unknown — code Y-997",
      "L-143": "Unknown — code L-143",
      "Y-859": "Unknown — code Y-859",
      "Y-959": "Unknown — code Y-959",
      "L-139": "Unknown — code L-139",
      "Y-824": "Unknown — code Y-824",
      "Y-878": "Unknown — code Y-878"
    },
    "stacked_measures": [
      {
        "hs_code": "7208510000",
        "market": "EU",
        "origin_code": "1008",
        "origin_name": "All third countries",
        "origin_code_type": "group_numeric",
        "measure_type": "IMPORT_CONTROL",
        "rate_basis": "import_control",
        "duty_rate": null,
        "duty_amount": null,
        "rate_specific_unit": null,
        "valid_from": "2023-12-19",
        "valid_to": "2026-12-31",
        "source": "TARIC",
        "ingested_at": "2026-03-29T02:19:46.912261+00:00",
        "details": {
          "measure_type_text": "Import control",
          "measure_type_code": "763",
          "origin_text": "All third countries",
          "origin_code_raw": "1008",
          "legal_base": "Regulation 0833/14",
          "regulation": null,
          "additional_code": null,
          "order_no": null,
          "duty_text": "Cond:  Y cert: L-139 (29):; Y cert: Y-824 (29):; Y cert: Y-878 (29):; Y cert: Y-859 (29):; Y cert: L-143 (29):; Y (09):"
        }
      },
      {
        "hs_code": "7208510000",
        "market": "EU",
        "origin_code": "RU",
        "origin_name": "RU",
        "origin_code_type": "country",
        "measure_type": "IMPORT_CONTROL",
        "rate_basis": "import_control",
        "duty_rate": null,
        "duty_amount": null,
        "rate_specific_unit": null,
        "valid_from": "2023-12-19",
        "valid_to": "2026-12-31",
        "source": "TARIC",
        "ingested_at": "2026-03-29T02:19:46.904006+00:00",
        "details": {
          "measure_type_text": "Import control",
          "measure_type_code": "763",
          "origin_text": "Russian Federation",
          "origin_code_raw": "RU",
          "legal_base": "Regulation 0833/14",
          "regulation": null,
          "additional_code": null,
          "order_no": null,
          "duty_text": "Cond:  Y cert: L-139 (29):; Y cert: L-143 (29):; Y cert: Y-859 (29):; Y (09):"
        }
      },
      {
        "hs_code": "7208510000",
        "market": "EU",
        "origin_code": "5005",
        "origin_name": "5005",
        "origin_code_type": "safeguard",
        "measure_type": "SAFEGUARD",
        "rate_basis": "safeguard",
        "duty_rate": 25,
        "duty_amount": null,
        "rate_specific_unit": null,
        "valid_from": "2025-04-01",
        "valid_to": "2026-06-30",
        "source": "TARIC",
        "ingested_at": "2026-03-29T02:19:46.897504+00:00",
        "details": {
          "measure_type_text": "Additional duties (safeguard)",
          "measure_type_code": "696",
          "origin_text": "Countries subject to safeguard measures",
          "origin_code_raw": "5005",
          "legal_base": "Regulation 0159/19",
          "regulation": null,
          "additional_code": null,
          "order_no": null,
          "duty_text": "25.000 %"
        }
      },
      {
        "hs_code": "7208000000",
        "market": "EU",
        "origin_code": "KP",
        "origin_name": "KP",
        "origin_code_type": "country",
        "measure_type": "IMPORT_CONTROL",
        "rate_basis": "import_control",
        "duty_rate": null,
        "duty_amount": null,
        "rate_specific_unit": null,
        "valid_from": "2017-09-16",
        "valid_to": null,
        "source": "TARIC",
        "ingested_at": "2026-03-29T02:19:43.672418+00:00",
        "details": {
          "measure_type_text": "Import control on restricted goods and technologies",
          "measure_type_code": "711",
          "origin_text": "North Korea (Democratic People’s Republic of Korea)",
          "origin_code_raw": "KP",
          "legal_base": "Regulation 1548/17",
          "regulation": null,
          "additional_code": null,
          "order_no": null,
          "duty_text": "Cond:  Y cert: Y-959 (29):; Y (09):"
        }
      },
      {
        "hs_code": "7200000000",
        "market": "EU",
        "origin_code": "UA",
        "origin_name": "UA",
        "origin_code_type": "country",
        "measure_type": "IMPORT_CONTROL",
        "rate_basis": "import_control",
        "duty_rate": null,
        "duty_amount": null,
        "rate_specific_unit": null,
        "valid_from": "2025-01-01",
        "valid_to": null,
        "source": "TARIC",
        "ingested_at": "2026-03-29T02:19:41.732025+00:00",
        "details": {
          "measure_type_text": "Import control",
          "measure_type_code": "760",
          "origin_text": "Ukraine",
          "origin_code_raw": "UA",
          "legal_base": "Regulation 0692/14",
          "regulation": null,
          "additional_code": null,
          "order_no": null,
          "duty_text": "Cond:  Y cert: Y-997 (26):; Y cert: U-078 (26):; Y cert: U-079 (26):; Y cert: N-954 (26):; Y cert: U-045 (26):; Y (06):"
        }
      },
      {
        "hs_code": "7200000000",
        "market": "EU",
        "origin_code": "UA",
        "origin_name": "UA",
        "origin_code_type": "country",
        "measure_type": "IMPORT_CONTROL",
        "rate_basis": "import_control",
        "duty_rate": null,
        "duty_amount": null,
        "rate_specific_unit": null,
        "valid_from": "2025-01-01",
        "valid_to": null,
        "source": "TARIC",
        "ingested_at": "2026-03-29T02:19:41.725202+00:00",
        "details": {
          "measure_type_text": "Import control",
          "measure_type_code": "762",
          "origin_text": "Ukraine",
          "origin_code_raw": "UA",
          "legal_base": "Regulation 0263/22",
          "regulation": null,
          "additional_code": null,
          "order_no": null,
          "duty_text": "Cond:  Y cert: Y-984 (29):; Y cert: N-954 (29):; Y cert: U-045 (29):; Y cert: U-078 (29):; Y cert: U-079 (29):; Y (09):"
        }
      }
    ],
    "duty": {
      "rate_type": "PREFERENTIAL",
      "duty_rate": 0,
      "duty_amount": null,
      "currency": null,
      "duty_unit": null,
      "duty_unit_description": null,
      "duty_amount_secondary": null,
      "duty_unit_secondary": null,
      "duty_min_amount": null,
      "duty_max_amount": null,
      "duty_min_rate": null,
      "duty_max_rate": null,
      "duty_max_total_rate": null,
      "has_entry_price": false,
      "entry_price_type": null,
      "is_nihil": false,
      "is_alcohol_duty": false,
      "anti_dumping_specific": false,
      "siv_bands": null,
      "trade_agreement": null,
      "financial_charge": true,
      "source": "TARIC",
      "origin_code": "GB",
      "origin_name": "GB",
      "rate_basis": "bilateral_preference",
      "conditions": [],
      "human_readable": "0%"
    },
    "vat": {
      "country_code": "DE",
      "rate_type": "standard",
      "vat_rate": 19,
      "hs_code_prefix": null,
      "source": "euvatrates"
    },
    "calculated": {
      "duty_on_goods_value_pct": 0,
      "effective_duty_rate": null,
      "effective_duty_amount": null,
      "effective_duty_unit": null,
      "variable_rate_evaluated": false,
      "entry_price_component": false,
      "vat_applies_to": "goods_value + duty",
      "note": "VAT is assessed on CIF value + customs duty",
      "has_mfn_via_walkup": false,
      "mfn_duty": null,
      "warnings": []
    },
    "data_freshness": {
      "duty_last_updated": "2026-03-29",
      "vat_last_updated": "2026-03-29"
    },
    "other_measures": [
      {
        "hs_code": "7208510000",
        "destination_market": "EU",
        "destination_country": "DE",
        "origin_country": "1008",
        "measure_type": "IMPORT_CONTROL",
        "rate_ad_valorem": null,
        "rate_specific_amount": null,
        "rate_specific_unit": null,
        "valid_from": "2023-12-19",
        "valid_to": "2026-12-31",
        "source": "TARIC",
        "details": {
          "order_no": null,
          "add_code": null,
          "legal_base": "Regulation 0833/14",
          "duty_text": "Cond:  Y cert: L-139 (29):; Y cert: Y-824 (29):; Y cert: Y-878 (29):; Y cert: Y-859 (29):; Y cert: L-143 (29):; Y (09):",
          "measure_type_text": "Import control",
          "measure_type_code": "763",
          "origin_text": "All third countries",
          "origin_code": "1008"
        }
      }
    ],
    "tariff_quotas": [],
    "non_tariff_measures": [
      {
        "hs_code": "7208510000",
        "destination_market": "EU",
        "destination_country": "DE",
        "origin_country": "1008",
        "measure_type": "IMPORT_CONTROL",
        "rate_ad_valorem": null,
        "rate_specific_amount": null,
        "rate_specific_unit": null,
        "valid_from": "2023-12-19",
        "valid_to": "2026-12-31",
        "source": "TARIC",
        "details": {
          "order_no": null,
          "add_code": null,
          "legal_base": "Regulation 0833/14",
          "duty_text": "Cond:  Y cert: L-139 (29):; Y cert: Y-824 (29):; Y cert: Y-878 (29):; Y cert: Y-859 (29):; Y cert: L-143 (29):; Y (09):",
          "measure_type_text": "Import control",
          "measure_type_code": "763",
          "origin_text": "All third countries",
          "origin_code": "1008"
        }
      }
    ],
    "supplementary_units": [],
    "price_measures": []
  },
  "meta": {
    "request_id": "c6163414-9bed-4549-9e99-3d1c75361092",
    "timestamp": "2026-03-29T02:30:42.740432+00:00"
  }
}