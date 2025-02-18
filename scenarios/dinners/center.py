import itertools
import pandas as pd
from pathlib import Path


class DinnersEvaluator:
    """Evaluates the center utility value of a set of agreements/disagreements"""

    def __init__(self, reserved_value=0.0):
        self.reserved_value = reserved_value
        values = pd.read_csv(Path(__file__).parent / "center.csv")
        # read the utility values from the csv vile
        self.days = [_ for _ in values.columns if _ != "value"]
        self.n_days = len(self.days)
        self.values = dict()
        for _, row in values.iterrows():
            self.values[tuple(int(row[col]) for col in self.days)] = row["value"]

    def __call__(self, agreements):
        if not agreements:
            return self.reserved_value
        outings = dict(zip(self.days, itertools.repeat(0)))
        for agreement in agreements:
            if agreement is None:
                continue
            # day is a tuple of one value which is the day selected
            outings[agreement[0]] += 1
        return self.values.get(
            tuple(outings[day] for day in self.days), self.reserved_value
        )
