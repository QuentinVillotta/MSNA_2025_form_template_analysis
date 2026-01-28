"""Indicator Bank loader for MSNA 2025 analysis."""

from pathlib import Path
import pandas as pd
from loguru import logger


class IndicatorBankLoader:
    """Load and parse MSNA 2025 Indicator Bank Excel file.
    
    Provides access to indicator metadata including tier levels,
    question codes, and indicator definitions from the IB_2025_EN sheet.
    """
    
    def __init__(self, file_path: str | Path):
        """Initialize loader with file path.
        
        Args:
            file_path: Path to indicator_bank_MSNA_2025.xlsx file
        """
        self.file_path = Path(file_path)
        self._data: pd.DataFrame | None = None
    
    @property
    def data(self) -> pd.DataFrame:
        """Get indicator bank data, loading lazily if needed.
        
        Returns:
            DataFrame with indicator bank data
        """
        if self._data is None:
            self._load()
        return self._data
    
    def _load(self) -> None:
        """Load indicator bank from Excel file."""
        logger.info(f"Loading indicator bank from {self.file_path}")
        
        self._data = pd.read_excel(
            self.file_path,
            sheet_name="IB_2025_EN"
        )
        
        logger.success(
            f"Indicator bank loaded: {len(self._data)} indicators"
        )
    
    def get_question_codes(self) -> list[str]:
        """Get all question codes from indicator bank.
        
        Returns:
            List of question codes (variable names)
        """
        return self.data["Question code"].dropna().tolist()
    
    def get_by_tier(self, tier: int | str) -> pd.DataFrame:
        """Filter indicators by tier level.
        
        Args:
            tier: Tier level (1, 2, or 3)
            
        Returns:
            DataFrame with indicators matching tier
        """
        return self.data[
            self.data["Tier (1, 2 or 3)"].astype(str) == str(tier)
        ].copy()
    
    def get_by_theme(self, theme: str) -> pd.DataFrame:
        """Filter indicators by sector/theme.
        
        Args:
            theme: Sector/theme name
            
        Returns:
            DataFrame with indicators matching theme
        """
        return self.data[
            self.data["Sector/Theme"] == theme
        ].copy()
    
    def get_tier_distribution(self) -> pd.Series:
        """Get distribution of indicators by tier level.
        
        Returns:
            Series with tier counts
        """
        tier_counts = self.data["Tier (1, 2 or 3)"].value_counts()
        # Convert index to string for consistent sorting
        tier_counts.index = tier_counts.index.astype(str)
        return tier_counts.sort_index()
    
    def get_theme_distribution(self) -> pd.Series:
        """Get distribution of indicators by theme.
        
        Returns:
            Series with theme counts
        """
        return self.data["Sector/Theme"].value_counts()
    
    def get_question_types(self) -> pd.Series:
        """Get distribution of question types.
        
        Returns:
            Series with question type counts
        """
        return self.data["Question type"].value_counts()
    
    def get_indicator_details(self, question_code: str) -> pd.Series | None:
        """Get details for specific question code.
        
        Args:
            question_code: Question code to lookup
            
        Returns:
            Series with indicator details or None if not found
        """
        matches = self.data[self.data["Question code"] == question_code]
        if len(matches) == 0:
            return None
        return matches.iloc[0]


def load_indicator_bank(
    file_path: str | Path = "data/indicator_bank_MSNA_2025.xlsx"
) -> IndicatorBankLoader:
    """Convenience function to load indicator bank.
    
    Args:
        file_path: Path to indicator bank Excel file
        
    Returns:
        Loaded IndicatorBankLoader instance
    """
    loader = IndicatorBankLoader(file_path)
    _ = loader.data  # Trigger loading
    return loader
