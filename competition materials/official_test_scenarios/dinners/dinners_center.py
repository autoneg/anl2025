import itertools
import pandas as pd
from pathlib import Path


class DinnersEvaluator:
    """Evaluates the center utility value of a set of agreements/disagreements"""

    def __init__(self, reserved_value=0.0, values=None, days=None):
        self.reserved_value = reserved_value
        if values is None:
            # read the utility values from the csv vile
            values = pd.read_csv(Path(__file__).parent / "center.csv")
            self.days = [_ for _ in values.columns if _ != "value"]
            self.values = dict()
            for _, row in values.iterrows():
                self.values[str(tuple(int(row[col]) for col in self.days))] = row[
                    "value"
                ]
        else:
            self.days = days
            self.values = values

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
            str(tuple(outings[day] for day in self.days)), self.reserved_value
        )
