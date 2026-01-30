"""MSNA 2025 Country Compliance Analysis.

Analysis of template compliance across 14 country MSNAs including column presence,
indicator matching, and fuzzy matching for typo detection.
"""

import marimo

__generated_with = "0.19.6"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo
    import pandas as pd
    import plotly.express as px
    import plotly.graph_objects as go
    from pathlib import Path
    
    mo.md("""
    # MSNA 2025: Country Compliance Analysis
    
    **Objective**: Analyze template compliance across 14 country MSNAs to identify gaps,
    standardization issues, and potential improvements for the 2025 MSNA cycle.
    
    This analysis covers:
    1. Column presence analysis
    2. Indicator matching across countries
    3. Fuzzy matching for typo detection
    """)
    return go, mo, pd, Path, px


@app.cell
def _(Path, pd):
    # Load parquet data
    data_dir = Path("data/raw")
    
    assets_df = pd.read_parquet(data_dir / "assets.parquet")
    survey_df = pd.read_parquet(data_dir / "survey.parquet")
    
    # Load template and indicator bank
    from src.template import load_template
    from src.indicator_bank import load_indicator_bank
    
    template = load_template()
    ib = load_indicator_bank()
    
    return assets_df, ib, load_indicator_bank, load_template, survey_df, template


@app.cell
def _(assets_df, mo, survey_df, template):
    # Overview statistics
    n_projects = len(assets_df)
    n_countries = assets_df['country_code_settings'].nunique()
    n_questions = len(survey_df)
    n_template_indicators = len(template.survey[
        template.survey['type'].notna() & 
        ~template.survey['type'].str.startswith(('begin', 'end', 'note'))
    ])
    
    mo.md(f"""
    ## Data Overview
    
    - **Projects analyzed**: {n_projects}
    - **Countries**: {n_countries}
    - **Total questions in database**: {n_questions:,}
    - **Template indicators**: {n_template_indicators}
    """)
    return n_countries, n_projects, n_questions, n_template_indicators


@app.cell
def _(mo):
    mo.md("""
    ---
    ## 1. Column Presence Analysis
    
    Checks which template columns are present (and contain data) in each country MSNA.
    """)
    return


@app.cell
def _(assets_df, survey_df, template):
    from src.country_forms.column_presence import generate_column_presence_matrix
    
    # Get template columns (exclude index/analytical columns)
    template_columns = [
        col for col in template.survey.columns 
        if col not in ['Unnamed: 0'] and not col.startswith('Unnamed:')
    ]
    
    column_presence = generate_column_presence_matrix(
        template_columns=template_columns,
        assets_df=assets_df,
        survey_df=survey_df
    )
    return column_presence, generate_column_presence_matrix, template_columns


@app.cell
def _(column_presence, mo):
    # Display column presence matrix
    mo.md(f"""
    ### Column Presence Matrix
    
    Binary matrix showing template column presence across {len(column_presence)} projects.
    **1** = Column present with data, **0** = Column absent or empty.
    """)
    return


@app.cell
def _(column_presence, mo):
    # Calculate summary statistics
    presence_summary = column_presence.drop(columns=['country_code', 'submissions']).sum().sort_values(ascending=False)
    presence_df = pd.DataFrame({
        'Column': presence_summary.index,
        'Projects with Column': presence_summary.values,
        'Coverage %': (presence_summary.values / len(column_presence) * 100).round(1)
    })
    
    mo.ui.table(presence_df, selection=None, page_size=25)
    return presence_df, presence_summary


@app.cell
def _(column_presence, mo, px):
    # Visualize column coverage
    coverage_data = column_presence.drop(columns=['country_code', 'submissions']).sum().sort_values()
    
    fig_coverage = px.bar(
        x=coverage_data.values,
        y=coverage_data.index,
        orientation='h',
        title='Template Column Coverage Across All Projects',
        labels={'x': 'Number of Projects', 'y': 'Template Column'},
        color=coverage_data.values,
        color_continuous_scale='RdYlGn'
    )
    fig_coverage.update_layout(height=800, showlegend=False)
    
    mo.ui.plotly(fig_coverage)
    return coverage_data, fig_coverage


@app.cell
def _(mo):
    mo.md("""
    ---
    ## 2. Indicator Matching Analysis
    
    Analyzes which template indicators are present in each country MSNA.
    """)
    return


@app.cell
def _(assets_df, ib, survey_df, template):
    from src.country_forms.indicator_matching import (
        generate_indicator_match_matrix,
        generate_country_match_summary
    )
    
    # Generate indicator match matrix
    indicator_matrix = generate_indicator_match_matrix(
        template_survey_df=template.survey,
        ib_df=ib.data,
        country_survey_df=survey_df,
        assets_df=assets_df
    )
    
    # Generate country summary
    country_summary = generate_country_match_summary(
        template_survey_df=template.survey,
        ib_df=ib.data,
        country_survey_df=survey_df,
        assets_df=assets_df
    )
    return (
        country_summary,
        generate_country_match_summary,
        generate_indicator_match_matrix,
        indicator_matrix,
    )


@app.cell
def _(country_summary, mo):
    mo.md(f"""
    ### Country Match Summary
    
    Match statistics for {len(country_summary)} country MSNAs.
    """)
    return


@app.cell
def _(country_summary, mo):
    # Display summary table
    display_summary = country_summary[['country_code', 'n_total_indicators', 'n_matched', 'n_not_matched', 'match_pct']].copy()
    display_summary.columns = ['Country', 'Total Indicators', 'Matched', 'Not Matched', 'Match %']
    
    mo.ui.table(display_summary, selection=None, page_size=25)
    return (display_summary,)


@app.cell
def _(country_summary, mo, px):
    # Overall match visualization
    # Sort by match_pct ascending for proper bar ordering
    country_summary_sorted = country_summary.reset_index().sort_values('match_pct', ascending=True)
    
    fig_overall = px.bar(
        country_summary_sorted,
        x='match_pct',
        y='survey_name',
        orientation='h',
        title='Template Compliance by Country (%)',
        labels={'match_pct': 'Match %', 'survey_name': 'Survey'},
        color='match_pct',
        color_continuous_scale='RdYlGn',
        range_color=[0, 100],
        text='match_pct'
    )
    fig_overall.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
    fig_overall.update_layout(height=600, yaxis={'categoryorder': 'total ascending'})
    
    mo.md("### Overall Compliance")
    return (fig_overall,)


@app.cell
def _(fig_overall, mo):
    mo.ui.plotly(fig_overall)
    return


@app.cell
def _(assets_df, ib, indicator_matrix, mo, pd, px):
    # Match analysis by tier
    mo.md("""
    ### Compliance by Tier
    
    Breakdown by indicator priority (Tier 1=critical, 2=important, 3=optional).
    """)
    
    # Calculate tier-level statistics
    tier_stats = []
    
    for tier in [1.0, 2.0, 3.0]:
        tier_indicators = indicator_matrix[indicator_matrix['tier'] == tier]
        if len(tier_indicators) == 0:
            continue
        
        for survey_name in assets_df['name']:
            if survey_name in tier_indicators.columns:
                n_total = len(tier_indicators)
                n_matched = tier_indicators[survey_name].sum()
                match_pct = (n_matched / n_total * 100) if n_total > 0 else 0
                
                tier_stats.append({
                    'Survey': survey_name,
                    'Tier': f'Tier {tier}',
                    'Total': n_total,
                    'Matched': n_matched,
                    'Match %': match_pct
                })
    
    tier_df = pd.DataFrame(tier_stats)
    
    # Visualize tier compliance
    fig_tier = px.bar(
        tier_df,
        x='Match %',
        y='Survey',
        color='Tier',
        orientation='h',
        title='Template Compliance by Tier',
        labels={'Match %': 'Match %', 'Survey': 'Survey'},
        barmode='group',
        text='Match %'
    )
    fig_tier.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
    fig_tier.update_layout(height=600, yaxis={'categoryorder': 'total ascending'})
    
    mo.ui.plotly(fig_tier)
    return fig_tier, n_matched, n_total, survey_name, tier, tier_df, tier_indicators, tier_stats


@app.cell
def _(assets_df, indicator_matrix, mo, pd, px):
    # Match analysis by theme
    mo.md("""
    ### Compliance by Theme
    
    Breakdown by sector/theme.
    """)
    
    # Calculate theme-level statistics
    theme_stats = []
    
    for theme in indicator_matrix['theme'].dropna().unique():
        if pd.isna(theme) or theme == '':
            continue
        theme_indicators = indicator_matrix[indicator_matrix['theme'] == theme]
        if len(theme_indicators) == 0:
            continue
        
        for survey_name_theme in assets_df['name']:
            if survey_name_theme in theme_indicators.columns:
                n_total_theme = len(theme_indicators)
                n_matched_theme = theme_indicators[survey_name_theme].sum()
                match_pct_theme = (n_matched_theme / n_total_theme * 100) if n_total_theme > 0 else 0
                
                theme_stats.append({
                    'Survey': survey_name_theme,
                    'Theme': theme,
                    'Total': n_total_theme,
                    'Matched': n_matched_theme,
                    'Match %': match_pct_theme
                })
    
    theme_df = pd.DataFrame(theme_stats)
    
    # Get top themes by total indicators
    top_themes = theme_df.groupby('Theme')['Total'].first().sort_values(ascending=False).head(8).index
    theme_df_top = theme_df[theme_df['Theme'].isin(top_themes)]
    
    # Visualize theme compliance (heatmap)
    # Aggregate by mean in case of duplicates
    theme_pivot = theme_df_top.groupby(['Survey', 'Theme'])['Match %'].mean().reset_index().pivot(
        index='Survey', columns='Theme', values='Match %'
    ).fillna(0)
    
    fig_theme = px.imshow(
        theme_pivot,
        title='Template Compliance by Theme (Top 8 Themes)',
        labels={'x': 'Theme', 'y': 'Survey', 'color': 'Match %'},
        color_continuous_scale='RdYlGn',
        aspect='auto',
        text_auto='.1f'
    )
    fig_theme.update_layout(height=600)
    
    mo.ui.plotly(fig_theme)
    return (
        fig_theme,
        match_pct_theme,
        n_matched_theme,
        n_total_theme,
        survey_name_theme,
        theme,
        theme_df,
        theme_df_top,
        theme_indicators,
        theme_pivot,
        theme_stats,
        top_themes,
    )


@app.cell
def _(assets_df, ib, indicator_matrix, mo, pd, px):
    # Match analysis by theme AND tier
    mo.md("""
    ### Compliance by Theme × Tier
    
    Cross-analysis showing compliance for different theme-tier combinations.
    """)
    
    # Calculate theme-tier statistics
    theme_tier_stats = []
    
    for theme_tt in indicator_matrix['theme'].dropna().unique():
        if pd.isna(theme_tt) or theme_tt == '':
            continue
        for tier_tt in [1.0, 2.0, 3.0]:
            tt_indicators = indicator_matrix[
                (indicator_matrix['theme'] == theme_tt) & 
                (indicator_matrix['tier'] == tier_tt)
            ]
            if len(tt_indicators) == 0:
                continue
            
            for survey_name_tt in assets_df['name']:
                if survey_name_tt in tt_indicators.columns:
                    n_total_tt = len(tt_indicators)
                    n_matched_tt = tt_indicators[survey_name_tt].sum()
                    match_pct_tt = (n_matched_tt / n_total_tt * 100) if n_total_tt > 0 else 0
                    
                    theme_tier_stats.append({
                        'Survey': survey_name_tt,
                        'Theme': theme_tt,
                        'Tier': f'Tier {tier_tt}',
                        'Total': n_total_tt,
                        'Matched': n_matched_tt,
                        'Match %': match_pct_tt
                    })
    
    theme_tier_df = pd.DataFrame(theme_tier_stats)
    
    # Focus on top themes and Tier 1 for clarity
    top_themes_tt = theme_tier_df.groupby('Theme')['Total'].sum().sort_values(ascending=False).head(6).index
    theme_tier_df_filtered = theme_tier_df[
        (theme_tier_df['Theme'].isin(top_themes_tt)) & 
        (theme_tier_df['Tier'] == 'Tier 1')
    ]
    
    if len(theme_tier_df_filtered) > 0:
        fig_theme_tier = px.bar(
            theme_tier_df_filtered,
            x='Match %',
            y='Survey',
            color='Theme',
            orientation='h',
            title='Tier 1 Compliance by Theme (Top 6 Themes)',
            labels={'Match %': 'Match %', 'Survey': 'Survey'},
            barmode='group',
            text='Match %'
        )
        fig_theme_tier.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
        fig_theme_tier.update_layout(height=600, yaxis={'categoryorder': 'total ascending'})
        
        mo.ui.plotly(fig_theme_tier)
    else:
        mo.md("*No theme-tier data available.*")
    return (
        fig_theme_tier,
        match_pct_tt,
        n_matched_tt,
        n_total_tt,
        survey_name_tt,
        theme_tier_df,
        theme_tier_df_filtered,
        theme_tier_stats,
        theme_tt,
        tier_tt,
        top_themes_tt,
        tt_indicators,
    )


@app.cell
def _(mo):
    mo.md("""
    ---
    ## 3. Fuzzy Matching - Typo Detection
    
    Interactive analysis to detect near-matches between template and country indicators.
    Helps identify typos, plurals, and naming variations.
    """)
    return


@app.cell
def _(mo):
    # Create interactive controls for fuzzy matching
    similarity_slider = mo.ui.slider(
        start=70,
        stop=100,
        step=1,
        value=85,
        label="Similarity Threshold (%)",
        show_value=True
    )
    
    return (similarity_slider,)


@app.cell
def _(assets_df, mo):
    # Survey filter dropdown
    survey_options = ['All'] + assets_df['name'].tolist()
    survey_dropdown = mo.ui.dropdown(
        options=survey_options,
        value='All',
        label="Filter by Survey"
    )
    
    return survey_dropdown, survey_options


@app.cell
def _(mo, similarity_slider, survey_dropdown):
    mo.md("""
    ### Near-Match Detection
    
    Adjust the similarity threshold and filter by survey to explore potential typos.
    """)
    
    mo.hstack([similarity_slider, survey_dropdown])
    return


@app.cell
def _(assets_df, similarity_slider, survey_df, template):
    from src.country_forms.indicator_matching import detect_near_matches
    
    # Generate near-matches with current threshold
    near_matches = detect_near_matches(
        template_survey_df=template.survey,
        country_survey_df=survey_df,
        assets_df=assets_df,
        similarity_threshold=similarity_slider.value
    )
    return detect_near_matches, near_matches


@app.cell
def _(mo, near_matches, pd, similarity_slider, survey_dropdown):
    # Filter by selected survey
    if survey_dropdown.value == 'All':
        filtered_near_matches = near_matches
    else:
        filtered_near_matches = near_matches[near_matches['survey_name'] == survey_dropdown.value]
    
    # Display results
    if len(filtered_near_matches) > 0:
        display_cols = ['template_name', 'country_name', 'survey_name', 'country_code', 'similarity_score', 'length_diff', 'whitespace_only']
        display_near = filtered_near_matches[display_cols].copy()
        display_near.columns = ['Template Name', 'Country Name', 'Survey', 'Country', 'Similarity %', 'Length Diff', 'Whitespace Only']
        
        # Count whitespace-only issues
        n_whitespace = display_near['Whitespace Only'].sum()
        
        result = mo.vstack([
            mo.md(f"""
            **Found {len(filtered_near_matches)} near-matches** at threshold ≥ {similarity_slider.value}%
            
            - **{n_whitespace}** differences due to whitespace only (leading/trailing spaces)
            - **{len(filtered_near_matches) - n_whitespace}** other variations (typos, plurals, etc.)
            
            These represent potential data quality issues that should be standardized.
            """),
            mo.ui.table(display_near, selection=None, page_size=25)
        ])
    else:
        display_near = pd.DataFrame()
        result = mo.md(f"*No near-matches found at threshold ≥ {similarity_slider.value}%*")
    
    return display_cols, display_near, filtered_near_matches, result


@app.cell
def _(result):
    result
    return


@app.cell
def _(filtered_near_matches, go, mo, pd):
    # Visualize near-match distribution by country
    if len(filtered_near_matches) > 0:
        country_typo_counts = filtered_near_matches.groupby('country_code').size().sort_values(ascending=False)
        
        fig_typos = go.Figure(data=[
            go.Bar(
                x=country_typo_counts.values,
                y=country_typo_counts.index,
                orientation='h',
                marker=dict(
                    color=country_typo_counts.values,
                    colorscale='Reds',
                    showscale=True,
                    colorbar=dict(title="Count")
                ),
                text=country_typo_counts.values,
                textposition='outside'
            )
        ])
        
        fig_typos.update_layout(
            title='Near-Matches by Country',
            xaxis_title='Number of Near-Matches',
            yaxis_title='Country',
            height=500,
            yaxis={'categoryorder': 'total ascending'}
        )
        
        mo.ui.plotly(fig_typos)
    return country_typo_counts, fig_typos


@app.cell
def _(filtered_near_matches, mo, px):
    # Similarity score distribution
    if len(filtered_near_matches) > 0:
        fig_similarity_dist = px.histogram(
            filtered_near_matches,
            x='similarity_score',
            nbins=30,
            title='Distribution of Similarity Scores',
            labels={'similarity_score': 'Similarity %', 'count': 'Frequency'},
            color_discrete_sequence=['#3498db']
        )
        fig_similarity_dist.update_layout(height=400)
        
        mo.ui.plotly(fig_similarity_dist)
    return (fig_similarity_dist,)


@app.cell
def _(mo):
    mo.md("""
    ---
    ## Key Findings Summary
    
    - **Column Coverage**: Most countries have core question fields (type, name, required, relevant)
      but vary significantly in optional fields (labels, hints, calculations)
    - **Indicator Compliance**: Ranges from 87.9% (Ethiopia) to 1.6% (Ukraine)
    - **Tier Analysis**: Tier 1 (critical) indicators show better compliance than Tier 2/3
    - **Near-Matches**: Fuzzy matching reveals pluralization issues and minor spelling variations
      that can be standardized for future cycles
    """)
    return


if __name__ == "__main__":
    app.run()
