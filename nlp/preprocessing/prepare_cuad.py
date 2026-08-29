import ast
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]

CUAD_FILE = PROJECT_ROOT / "CUAD_v1" / "master_clauses.csv"

OUTPUT_DIR = PROJECT_ROOT / "nlp" / "data"
OUTPUT_FILE = OUTPUT_DIR / "cuad_clause_dataset.csv"

CLAUSE_CATEGORIES = {
    # Liability & financial risk
    "Cap On Liability": "liability_cap",
    "Uncapped Liability": "uncapped_liability",
    "Liquidated Damages": "liquidated_damages",
    "Insurance": "insurance",
    "Revenue/Profit Sharing": "revenue_profit_sharing",
    "Price Restrictions": "price_restrictions",
    "Minimum Commitment": "minimum_commitment",
    "Volume Restriction": "volume_restriction",

    # Term & termination
    "Termination For Convenience": "termination_for_convenience",
    "Renewal Term": "auto_renewal",
    "Notice Period To Terminate Renewal": "renewal_notice",
    "Post-Termination Services": "post_termination_services",

    # Legal / control
    "Governing Law": "governing_law",
    "Anti-Assignment": "anti_assignment",
    "Change Of Control": "change_of_control",
    "Third Party Beneficiary": "third_party_beneficiary",
    "Covenant Not To Sue": "covenant_not_to_sue",

    # Competition / restrictions
    "Non-Compete": "non_compete",
    "Competitive Restriction Exception": "competitive_restriction_exception",
    "Exclusivity": "exclusivity",
    "No-Solicit Of Customers": "customer_non_solicit",
    "No-Solicit Of Employees": "employee_non_solicit",
    "Non-Disparagement": "non_disparagement",

    # Intellectual property / licensing
    "Ip Ownership Assignment": "ip_ownership_assignment",
    "Joint Ip Ownership": "joint_ip_ownership",
    "License Grant": "license_grant",
    "Non-Transferable License": "non_transferable_license",
    "Affiliate License-Licensor": "affiliate_license_licensor",
    "Affiliate License-Licensee": "affiliate_license_licensee",
    "Unlimited/All-You-Can-Eat-License": "unlimited_license",
    "Irrevocable Or Perpetual License": "irrevocable_perpetual_license",
    "Source Code Escrow": "source_code_escrow",

    # Operational / commercial
    "Audit Rights": "audit_rights",
    "Most Favored Nation": "most_favored_nation",
    "Rofr/Rofo/Rofn": "right_of_first_refusal",
    "Warranty Duration": "warranty_duration",
}

def parse_cell(value):

    if pd.isna(value):
        return []

    try:
        parsed = ast.literal_eval(str(value))

        if isinstance(parsed, list):
            return parsed

        return [str(parsed)]

    except (ValueError, SyntaxError):
        return [str(value)]


# Main preprocessing

def main():

    print("Loading CUAD dataset...")

    df = pd.read_csv(CUAD_FILE)

    print(f"Contracts: {len(df)}")
    print(f"Columns: {len(df.columns)}")

    records = []

    for column, label in CLAUSE_CATEGORIES.items():

        print(f"\nProcessing: {column}")

        if column not in df.columns:

            print(f"WARNING: {column} not found.")
            continue

        count = 0

        for _, row in df.iterrows():

            clauses = parse_cell(row[column])

            for clause in clauses:

                clause = str(clause).strip()

                # Ignore empty or extremely short entries
                if len(clause) < 20:
                    continue

                records.append({
                    "clause_text": clause,
                    "label": label,
                    "source_contract": row["Filename"],
                })

                count += 1

        print(f"Clauses found: {count}")

    dataset = pd.DataFrame(records)

    dataset = dataset.drop_duplicates(
        subset=["clause_text", "label"]
    )

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    dataset.to_csv(
        OUTPUT_FILE,
        index=False,
        encoding="utf-8"
    )
    print("\n" + "=" * 60)
    print("CUAD PREPROCESSING COMPLETE")
    print("=" * 60)
    print(f"Total samples: {len(dataset)}")
    print("\nClass distribution:")
    print(dataset["label"].value_counts())
    print("\nSaved to:")
    print(OUTPUT_FILE)


if __name__ == "__main__":
    main()