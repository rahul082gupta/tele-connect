import pandas as pd
import numpy as np


class DataQualityProcessor:

    def __init__(self, df):

        self.df = df.copy()

        self.before_stats = (
            self.df
            .describe(include="all")
            .transpose()
        )

        self.issue_log = []

    # =====================================================
    # LOGGING
    # =====================================================

    def _log(
        self,
        column,
        issue,
        affected_rows,
        strategy
    ):

        self.issue_log.append({

            "column": column,

            "issue": issue,

            "affected_rows": int(
                affected_rows
            ),

            "strategy": strategy

        })

    # =====================================================
    # MISSING VALUES
    # =====================================================

    def _detect_missing_values(self):

        for col in self.df.columns:

            count = self.df[col].isna().sum()

            if count > 0:

                self._log(
                    col,
                    "Missing Values",
                    count,
                    "Imputed later"
                )

    # =====================================================
    # EMPTY STRINGS
    # =====================================================

    def _clean_empty_strings(self):

        for col in self.df.columns:

            count = (
                self.df[col]
                .astype(str)
                .str.strip()
                .eq("")
                .sum()
            )

            if count > 0:

                self._log(
                    col,
                    "Empty Strings",
                    count,
                    "Converted to NaN"
                )

        self.df.replace(
            r'^\s*$',
            np.nan,
            regex=True,
            inplace=True
        )

    # =====================================================
    # SENTINEL VALUES
    # =====================================================

    def _clean_sentinel_values(self):

        sentinels = [

            "NA",
            "N/A",
            "NULL",
            "UNKNOWN",
            "?",
            "-1",
            "999",
            "9999"

        ]

        for col in self.df.columns:

            count = (
                self.df[col]
                .astype(str)
                .isin(sentinels)
                .sum()
            )

            if count > 0:

                self._log(
                    col,
                    "Sentinel Values",
                    count,
                    "Converted to NaN"
                )

        self.df.replace(
            sentinels,
            np.nan,
            inplace=True
        )

    # =====================================================
    # DUPLICATES
    # =====================================================

    def _remove_duplicates(self):

        duplicate_rows = (
            self.df
            .duplicated()
            .sum()
        )

        if duplicate_rows > 0:

            self._log(
                "ALL_COLUMNS",
                "Duplicate Rows",
                duplicate_rows,
                "Removed"
            )

            self.df.drop_duplicates(
                inplace=True
            )

        if "customer_id" in self.df.columns:

            duplicate_customers = (
                self.df["customer_id"]
                .duplicated()
                .sum()
            )

            if duplicate_customers > 0:

                self._log(
                    "customer_id",
                    "Duplicate Customer IDs",
                    duplicate_customers,
                    "Retained for review"
                )

    # =====================================================
    # IMPOSSIBLE AGES
    # =====================================================

    def _clean_age(self):

        if "age" not in self.df.columns:
            return

        mask = (
            (self.df["age"] < 18)
            |
            (self.df["age"] > 100)
        )

        count = mask.sum()

        if count > 0:

            self._log(
                "age",
                "Impossible Age",
                count,
                "Set to NaN"
            )

            self.df.loc[
                mask,
                "age"
            ] = np.nan

    # =====================================================
    # IMPOSSIBLE TENURE
    # =====================================================

    def _clean_tenure(self):

        if "tenure_months" not in self.df.columns:
            return

        mask = (
            (self.df["tenure_months"] < 0)
            |
            (self.df["tenure_months"] > 120)
        )

        count = mask.sum()

        if count > 0:

            self._log(
                "tenure_months",
                "Impossible Tenure",
                count,
                "Set to NaN"
            )

            self.df.loc[
                mask,
                "tenure_months"
            ] = np.nan

    # =====================================================
    # NEGATIVE CHARGES
    # =====================================================

    def _clean_charges(self):

        charge_cols = [

            "monthly_charges",
            "total_charges"

        ]

        for col in charge_cols:

            if col not in self.df.columns:
                continue

            mask = self.df[col] < 0

            count = mask.sum()

            if count > 0:

                self._log(
                    col,
                    "Negative Charges",
                    count,
                    "Set to NaN"
                )

                self.df.loc[
                    mask,
                    col
                ] = np.nan

    # =====================================================
    # CATEGORICAL STANDARDIZATION
    # =====================================================

    def _standardize_categories(self):

        mappings = {

            "gender": {

                "male": "Male",
                "MALE": "Male",
                "M": "Male",

                "female": "Female",
                "FEMALE": "Female",
                "F": "Female"

            },

            "phone_service": {

                "yes": "Yes",
                "Y": "Yes",

                "no": "No",
                "N": "No"

            },

            "internet_service": {

                "fiber": "Fiber optic",
                "dsl": "DSL"

            },

            "payment_method": {

                "credit card": "Credit card",
                "CC": "Credit card",

                "bank transfer": "Bank transfer",
                "BT": "Bank transfer"

            }

        }

        for col, mapping in mappings.items():

            if col not in self.df.columns:
                continue

            before_unique = (
                self.df[col]
                .nunique(
                    dropna=True
                )
            )

            self.df[col] = (
                self.df[col]
                .replace(mapping)
            )

            after_unique = (
                self.df[col]
                .nunique(
                    dropna=True
                )
            )

            affected = (
                before_unique -
                after_unique
            )

            if affected > 0:

                self._log(
                    col,
                    "Inconsistent Encoding",
                    affected,
                    "Standardized Categories"
                )

    # =====================================================
    # SEMANTIC OUTLIERS
    # =====================================================

    def _detect_outliers(self):

        numeric_cols = self.df.select_dtypes(
            include=np.number
        ).columns

        for col in numeric_cols:

            if col == "churned":
                continue

            q1 = self.df[col].quantile(
                0.25
            )

            q3 = self.df[col].quantile(
                0.75
            )

            iqr = q3 - q1

            lower = (
                q1 -
                1.5 * iqr
            )

            upper = (
                q3 +
                1.5 * iqr
            )

            count = (

                (
                    self.df[col] < lower
                )

                |

                (
                    self.df[col] > upper
                )

            ).sum()

            if count > 0:

                self._log(
                    col,
                    "Potential Outliers",
                    count,
                    "Retained for modeling"
                )

    # =====================================================
    # IMPUTATION
    # =====================================================

    def _impute(self):

        numeric_cols = self.df.select_dtypes(
            include=np.number
        ).columns

        categorical_cols = self.df.select_dtypes(
            include="object"
        ).columns

        for col in numeric_cols:

            self.df[col] = (
                self.df[col]
                .fillna(
                    self.df[col]
                    .median()
                )
            )

        for col in categorical_cols:

            if (
                self.df[col]
                .mode()
                .empty
            ):
                continue

            self.df[col] = (
                self.df[col]
                .fillna(
                    self.df[col]
                    .mode()[0]
                )
            )

    # =====================================================
    # MAIN ENTRY
    # =====================================================

    def clean(self):

        self._detect_missing_values()

        self._clean_empty_strings()

        self._clean_sentinel_values()

        self._remove_duplicates()

        self._clean_age()

        self._clean_tenure()

        self._clean_charges()

        self._standardize_categories()

        self._detect_outliers()

        self._impute()

        return self.df

    # =====================================================
    # REPORTS
    # =====================================================

    def issue_report(self):

        return pd.DataFrame(
            self.issue_log
        )

    def statistics_report(self):

        after_stats = (

            self.df
            .describe(include="all")
            .transpose()

        )

        report = pd.concat(

            [

                self.before_stats.add_prefix(
                    "before_"
                ),

                after_stats.add_prefix(
                    "after_"
                )

            ],

            axis=1

        )

        return report