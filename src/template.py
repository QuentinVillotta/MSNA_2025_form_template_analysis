"""Template loader for MSNA 2025 reference form."""

from pathlib import Path
from typing import Tuple

import pandas as pd
from loguru import logger


class TemplateLoader:
    """Load and parse MSNA 2025 template Excel file."""
    
    def __init__(self, template_path: str = "data/kobo_form_template_MSNA_2025.xlsx"):
        """
        Initialize template loader.
        
        Args:
            template_path: Path to template Excel file
        """
        self.template_path = Path(template_path)
        if not self.template_path.exists():
            raise FileNotFoundError(f"Template file not found: {template_path}")
        
        self._survey = None
        self._choices = None
    
    def load(self) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Load survey and choices sheets from template.
        
        Returns:
            Tuple of (survey_df, choices_df)
        """
        if self._survey is None or self._choices is None:
            logger.info(f"Loading MSNA 2025 template from {self.template_path}")
            self._survey = pd.read_excel(self.template_path, sheet_name="survey")
            self._choices = pd.read_excel(self.template_path, sheet_name="choices")
            
            # Remove unnamed columns created by pandas when reading Excel
            self._survey = self._survey.loc[:, ~self._survey.columns.str.startswith('Unnamed:')]
            
            logger.success(f"Template loaded: {len(self._survey)} survey rows, {len(self._choices)} choice rows")
        
        return self._survey.copy(), self._choices.copy()
    
    @property
    def survey(self) -> pd.DataFrame:
        """Get survey sheet."""
        if self._survey is None:
            self.load()
        return self._survey.copy()
    
    @property
    def choices(self) -> pd.DataFrame:
        """Get choices sheet."""
        if self._choices is None:
            self.load()
        return self._choices.copy()
    
    def get_question_names(self) -> list[str]:
        """Get all question names from survey."""
        df = self.survey
        return df[df['name'].notna()]['name'].tolist()
    
    def get_choice_lists(self) -> list[str]:
        """Get all unique choice list names."""
        df = self.choices
        return df[df['list_name'].notna()]['list_name'].unique().tolist()
    
    def get_questions_by_level(self, level: str) -> pd.DataFrame:
        """
        Filter survey questions by level.
        
        Args:
            level: Level to filter (e.g., 'metadata', 'core', 'additional')
            
        Returns:
            Filtered DataFrame
        """
        df = self.survey
        return df[df['level'] == level].copy()
    
    def get_questions_by_theme(self, theme: str) -> pd.DataFrame:
        """
        Filter survey questions by theme.
        
        Args:
            theme: Theme to filter
            
        Returns:
            Filtered DataFrame
        """
        df = self.survey
        return df[df['theme'] == theme].copy()


def load_template(
    file_path: str | Path = "data/kobo_form_template_MSNA_2025.xlsx"
) -> TemplateLoader:
    """
    Convenience function to load template.
    
    Args:
        file_path: Path to template Excel file
        
    Returns:
        Loaded TemplateLoader instance
    """
    loader = TemplateLoader(file_path)
    _ = loader.survey  # Trigger loading
    return loader
