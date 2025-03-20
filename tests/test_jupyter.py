from __future__ import annotations
from pathlib import Path

import papermill as pm
import pytest


def notebooks():
    base = Path(__file__).parent.parent / "notebooks"
    return list(_ for _ in base.glob("**/*.ipynb") if "checkpoints" not in str(_))


# @pytest.skip(
#     "The tutorials use hard-coded paths!! cannot test them", allow_module_level=True
# )
@pytest.mark.parametrize("notebook", notebooks())
def test_notebook(notebook):
    base = Path(__file__).parent.parent / "notebooks"
    dst = notebook.relative_to(base)
    dst = Path(__file__).parent.parent / "tmp_notebooks" / str(dst)
    dst.parent.mkdir(exist_ok=True, parents=True)
    pm.execute_notebook(notebook, dst)


if __name__ == "__main__":
    print(notebooks())
