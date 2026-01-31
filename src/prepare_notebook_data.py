"""Prepare data for standalone notebook deployment.

This script loads template and indicator bank data and saves them as pickle files
for use in standalone Marimo notebooks (especially WASM exports).
"""

import pickle
from pathlib import Path
from loguru import logger

from src.template import load_template
from src.indicator_bank import load_indicator_bank


def prepare_data(output_dir: str | Path = "data/notebook_cache") -> None:
    """
    Load and serialize template and IB data for notebook use.
    
    Args:
        output_dir: Directory to save pickle files
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    logger.info("Loading template...")
    template = load_template()
    
    logger.info("Loading indicator bank...")
    indicator_bank = load_indicator_bank()
    
    # Save survey and data DataFrames
    template_data = {
        'survey': template.survey,
        'choices': template.choices
    }
    
    ib_data = {
        'data': indicator_bank.data,
        'question_codes': list(indicator_bank.get_question_codes())
    }
    
    template_file = output_path / "template_data.pkl"
    ib_file = output_path / "ib_data.pkl"
    
    logger.info(f"Saving template to {template_file}...")
    with open(template_file, 'wb') as f:
        pickle.dump(template_data, f)
    
    logger.info(f"Saving indicator bank to {ib_file}...")
    with open(ib_file, 'wb') as f:
        pickle.dump(ib_data, f)
    
    logger.success(f"Data prepared successfully in {output_path}")
    logger.info(f"  - Template: {len(template.survey)} rows")
    logger.info(f"  - IB: {len(indicator_bank.data)} rows")


if __name__ == "__main__":
    prepare_data()
