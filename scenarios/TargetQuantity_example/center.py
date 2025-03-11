import pandas as pd
from pathlib import Path


class TargetEvaluator:
    """Evaluates the center utility value of a set of agreements/disagreements"""

    def __init__(self, reserved_value=0.0, values=None):
        self.reserved_value = reserved_value
        if not values:
            values = pd.read_csv(Path(__file__).parent / "center.csv")
            self.values = dict()

            for _, row in values.iterrows():
                self.values[int(row["quantity"])] = float(row["value"])
        else:
            self.values = values
        # read the utility values from the csv vile

    def __call__(self, agreements):
        if not agreements:
            return self.reserved_value

        # outings = dict(zip(self.days, itertools.repeat(0)))
        quantity_sum = 0
        for agreement in agreements:
            if agreement is None:
                continue
            quantity_sum += int(agreement[0])
        return self.values.get(quantity_sum, self.reserved_value)
