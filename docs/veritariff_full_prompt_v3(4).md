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
        "rate_basis": null,
        "rate_type": null,
        "duty_rate": null,
        "duty_amount": null,
        "duty_unit": null,
        "valid_from": null,
        "valid_to": null,
        "source": null,
        "duty_expression": null,
        "human_readable": null,
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
        "rate_basis": null,
        "rate_type": null,
        "duty_rate": null,
        "duty_amount": null,
        "duty_unit": null,
        "valid_from": null,
        "valid_to": null,
        "source": null,
        "duty_expression": null,
        "human_readable": null,
        "conditions": []
      }
    ],
    "best_rate": null,
    "available_origin_codes": [
      "1008",
      "5005",
      "ID",
      "IN",
      "KR",
      "RU",
      "TR"
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
        "origin_code": "KR",
        "origin_name": "KR",
        "origin_code_type": "country",
        "measure_types": [
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
      ]
    },
    "certificate_codes": [
      "L-139",
      "L-143",
      "Y-824",
      "Y-859",
      "Y-878"
    ],
    "certificate_details": {
      "L-143": "Unknown — code L-143",
      "Y-859": "Unknown — code Y-859",
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
      }
    ],
    "duty": {
      "rate_type": null,
      "duty_rate": null,
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
      "financial_charge": null,
      "source": null,
      "origin_code": null,
      "origin_name": null,
      "rate_basis": null,
      "conditions": [],
      "human_readable": null
    },
    "vat": {
      "country_code": "DE",
      "rate_type": "standard",
      "vat_rate": 19,
      "hs_code_prefix": null,
      "source": "euvatrates"
    },
    "calculated": {
      "duty_on_goods_value_pct": null,
      "effective_duty_rate": null,
      "effective_duty_amount": null,
      "effective_duty_unit": null,
      "variable_rate_evaluated": false,
      "entry_price_component": false,
      "vat_applies_to": "goods_value + duty",
      "note": "VAT is assessed on CIF value + customs duty",
      "has_mfn_via_walkup": false,
      "mfn_duty": null,
      "warnings": [
        "No duty record matched the resolved origin codes. Try another origin or review full_report records."
      ]
    },
    "data_freshness": {
      "duty_last_updated": null,
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
    "request_id": "7b5b9aad-6155-4bdc-8931-08e0e15ef3f4",
    "timestamp": "2026-03-29T02:22:29.220629+00:00"
  }
}