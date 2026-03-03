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
    import shutil
    import importlib
    import sys

    # Force reload of src modules to ensure latest changes are used
    modules_to_reload = [
        'src.data_loader',
        'src.country_forms.choices_matching',
        'src.country_forms.indicator_matching',
        'src.country_forms.column_presence'
    ]
    for module_name in modules_to_reload:
        if module_name in sys.modules:
            importlib.reload(sys.modules[module_name])

    mo.md("""
    # MSNA 2025: Country Compliance Analysis

    **Objective**: Analyze template compliance across 14 country MSNAs to identify gaps,
    standardization issues, and potential improvements for the 2025 MSNA cycle.

    This analysis covers:
    1. Column presence analysis
    2. Indicator matching across countries
    3. Fuzzy matching for typo detection
    """)
    return Path, go, importlib, mo, pd, px, sys


@app.cell
def _(Path, pd):
    # Load parquet data with corrections applied
    from src.data_loader import load_data
    from src.template import load_template
    from src.indicator_bank import load_indicator_bank

    # Load data (includes data corrections: project filtering, country fixes, display names)
    assets_df, survey_df_raw, choices_df = load_data("data/raw")
    
    # Use display_name as the main name for all analyses and visualizations
    # Keep original name for reference if needed
    assets_df['name_original'] = assets_df['name']
    assets_df['name'] = assets_df['display_name']
    
    # NORMALIZE WHITESPACE IN QUESTION NAMES (AT SOURCE)
    # Strip leading/trailing whitespace immediately after loading
    # This ensures ALL subsequent analysis works with clean names
    survey_df_raw['name'] = survey_df_raw['name'].apply(
        lambda x: str(x).strip() if pd.notna(x) else x
    )

    # Load template and indicator bank
    template = load_template()
    ib = load_indicator_bank()

    return assets_df, choices_df, ib, survey_df_raw, template


@app.cell
def _(Path, assets_df, choices_df, mo, pd, shutil, survey_df_raw, template):
    """
    Normalize Ukraine project variable names.
    
    Ukraine project uses section prefixes (A_1_, B_2_, etc.) before variable names.
    This cell removes those prefixes to match template naming.
    """
    # Ukraine project UID
    _ukraine_uid = 'aCdzAaiGS5hAyMukmda6FW'
    
    # Build mapping for Ukraine questions to template names
    _template_names = set(template.survey['name'].dropna().tolist())
    _ukraine_name_mapping = {}
    
    # Get Ukraine questions from original data
    _ukraine_questions = survey_df_raw[survey_df_raw['asset_uid'] == _ukraine_uid]['name'].dropna().unique()
    
    for _ukraine_q in _ukraine_questions:
        # Check if it matches template directly
        if _ukraine_q in _template_names:
            continue
            
        # Check if any template name is a suffix (separated by underscore)
        for _template_q in _template_names:
            if _ukraine_q.endswith(_template_q):
                # Verify it's separated by underscore (not just substring)
                if len(_ukraine_q) > len(_template_q) and _ukraine_q[len(_ukraine_q)-len(_template_q)-1] == '_':
                    _ukraine_name_mapping[_ukraine_q] = _template_q
                    break
    
    # Create normalized survey_df
    survey_df = survey_df_raw.copy()
    
    # Apply transformation only for Ukraine project
    _ukraine_mask = survey_df['asset_uid'] == _ukraine_uid
    survey_df.loc[_ukraine_mask, 'name'] = survey_df.loc[_ukraine_mask, 'name'].map(
        lambda x: _ukraine_name_mapping.get(x, x)
    )
    
    # ALSO normalize choices data for Ukraine (used by choices analysis)
    # NOTE: We work on the choices_df loaded by load_data() which already has corrections applied
    # This preserves data corrections (filtered projects, country fixes)
    choices_df_normalized = choices_df.copy()
    
    # Apply same normalization to question_name column in choices
    _ukraine_choices_mask = choices_df_normalized['asset_uid'] == _ukraine_uid
    if 'question_name' in choices_df_normalized.columns and _ukraine_choices_mask.any():
        choices_df_normalized.loc[_ukraine_choices_mask, 'question_name'] = choices_df_normalized.loc[
            _ukraine_choices_mask, 'question_name'
        ].map(lambda x: _ukraine_name_mapping.get(x, x) if pd.notna(x) else x)
        
        _n_choices_normalized = choices_df_normalized.loc[
            _ukraine_choices_mask, 'question_name'
        ].isin(_ukraine_name_mapping.values()).sum()
        print(f"✓ Normalized {_n_choices_normalized} choice references for Ukraine")
    
    # Stats
    _n_ukraine_questions = len(_ukraine_questions)
    _n_normalized = len(_ukraine_name_mapping)
    _pct_normalized = (_n_normalized / _n_ukraine_questions * 100) if _n_ukraine_questions > 0 else 0
    
    print(f"✓ Ukraine survey normalization: {_n_normalized}/{_n_ukraine_questions} questions ({_pct_normalized:.1f}%) mapped to template names")
    
    return choices_df_normalized, survey_df
    

@app.cell
def _(mo, survey_df, template):
    # Debug: Verify normalization was applied
    _ukraine_uid = 'aCdzAaiGS5hAyMukmda6FW'
    _ukraine_data = survey_df[survey_df['asset_uid'] == _ukraine_uid]
    _template_names = set(template.survey['name'].dropna())
    _matches = set(_ukraine_data['name'].dropna()) & _template_names
    
    mo.md(f"""
    **Debug - Normalization Check:**
    - Ukraine questions in survey_df: {len(_ukraine_data)}
    - Matches with template: {len(_matches)}
    - Examples: {', '.join(sorted(list(_matches))[:10])}
    """)
    return


@app.cell
def _(assets_df, mo, survey_df, template):
    # Overview statistics (using normalized survey_df)
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
    return (column_presence,)


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
def _(column_presence, mo, pd):
    # Calculate summary statistics
    presence_summary = column_presence.drop(columns=['country_code', 'submissions']).sum().sort_values(ascending=False)
    presence_df = pd.DataFrame({
        'Column': presence_summary.index,
        'Projects with Column': presence_summary.values,
        'Coverage %': (presence_summary.values / len(column_presence) * 100).round(1)
    })

    mo.ui.table(presence_df, selection=None, page_size=25)
    return


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
    return


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
    return country_summary, indicator_matrix


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
    display_summary = country_summary[['country_code', 'submissions', 'n_total_indicators', 'n_matched', 'n_not_matched', 'match_pct']].copy()
    display_summary.columns = ['Country', 'Submissions', 'Total Indicators', 'Matched', 'Not Matched', 'Match %']

    mo.ui.table(display_summary, selection=None, page_size=25)
    return


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
    fig_overall.update_layout(height=600, yaxis={'categoryorder': 'trace'})

    mo.md("### Overall Compliance")
    return (fig_overall,)


@app.cell
def _(fig_overall, mo):
    mo.ui.plotly(fig_overall)
    return


@app.cell
def _(assets_df, indicator_matrix, mo, pd, px):
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

        for _survey_name in assets_df['name']:
            if _survey_name in tier_indicators.columns:
                n_total = len(tier_indicators)
                n_matched = tier_indicators[_survey_name].sum()
                _match_pct = (n_matched / n_total * 100) if n_total > 0 else 0

                tier_stats.append({
                    'Survey': _survey_name,
                    'Tier': f'Tier {tier}',
                    'Total': n_total,
                    'Matched': n_matched,
                    'Match %': _match_pct
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
    return


@app.cell
def _(assets_df, indicator_matrix, mo, pd, px):
    # Tier 1 only analysis
    mo.md("""
    ### Critical Indicators Compliance (Tier 1 Only)
    
    Percentage of critical (Tier 1) template indicators present in each country project.
    """)

    # Calculate Tier 1 statistics only
    tier1_stats = []
    
    tier1_indicators = indicator_matrix[indicator_matrix['tier'] == 1.0]
    
    for _survey_name_t1 in assets_df['name']:
        if _survey_name_t1 in tier1_indicators.columns:
            n_total_t1 = len(tier1_indicators)
            n_matched_t1 = tier1_indicators[_survey_name_t1].sum()
            _match_pct_t1 = (n_matched_t1 / n_total_t1 * 100) if n_total_t1 > 0 else 0

            tier1_stats.append({
                'Survey': _survey_name_t1,
                'Total': n_total_t1,
                'Matched': n_matched_t1,
                'Match %': _match_pct_t1
            })

    tier1_df = pd.DataFrame(tier1_stats).sort_values('Match %', ascending=True)

    # Visualize Tier 1 compliance with blue bars
    fig_tier1 = px.bar(
        tier1_df,
        x='Match %',
        y='Survey',
        orientation='h',
        title=f'Tier 1 Critical Indicators Compliance',
        labels={'Match %': 'Compliance Rate (%)', 'Survey': 'Country Project'},
        text='Match %'
    )
    fig_tier1.update_traces(
        texttemplate='%{text:.1f}%', 
        textposition='outside',
        marker_color='#3498db'  # Blue color
    )
    fig_tier1.update_layout(
        height=600, 
        yaxis={'categoryorder': 'trace'},
        xaxis={'range': [0, 110]}
    )

    mo.ui.plotly(fig_tier1)
    return


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

        for _survey_name_theme in assets_df['name']:
            if _survey_name_theme in theme_indicators.columns:
                n_total_theme = len(theme_indicators)
                n_matched_theme = theme_indicators[_survey_name_theme].sum()
                _match_pct_theme = (n_matched_theme / n_total_theme * 100) if n_total_theme > 0 else 0

                theme_stats.append({
                    'Survey': _survey_name_theme,
                    'Theme': theme,
                    'Total': n_total_theme,
                    'Matched': n_matched_theme,
                    'Match %': _match_pct_theme
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
    return


@app.cell
def _(assets_df, indicator_matrix, mo, pd, px):
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

            for _survey_name_tt in assets_df['name']:
                if _survey_name_tt in tt_indicators.columns:
                    n_total_tt = len(tt_indicators)
                    n_matched_tt = tt_indicators[_survey_name_tt].sum()
                    _match_pct_tt = (n_matched_tt / n_total_tt * 100) if n_total_tt > 0 else 0

                    theme_tier_stats.append({
                        'Survey': _survey_name_tt,
                        'Theme': theme_tt,
                        'Tier': f'Tier {tier_tt}',
                        'Total': n_total_tt,
                        'Matched': n_matched_tt,
                        'Match %': _match_pct_tt
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
    return


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

    return (survey_dropdown,)


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
    return (near_matches,)


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

    return filtered_near_matches, result


@app.cell
def _(result):
    result
    return


@app.cell
def _(filtered_near_matches, go, mo):
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
    return


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
    return


@app.cell
def _(mo):
    mo.md("""
    ---
    ## 4. Choices Compliance Analysis

    Analyzes consistency of answer choices (select_one/select_multiple options) between 
    template and country forms.
    """)
    return


@app.cell
def _(assets_df, choices_df_normalized, survey_df, template):
    from src.country_forms.choices_matching import (
        load_template_choices,
        extract_country_choices,
        generate_list_name_matrix,
        generate_list_name_summary,
        compare_choices_for_list
    )

    # Load template choices
    template_choices = load_template_choices(template)

    # Extract country choices (pass choices_df_normalized to use corrected + normalized data)
    country_choices = extract_country_choices(survey_df, assets_df, choices_df_normalized)

    # Generate list-level analysis
    list_name_matrix = generate_list_name_matrix(template_choices, country_choices)
    list_name_summary = generate_list_name_summary(template_choices, country_choices)

    return (country_choices, list_name_matrix, list_name_summary, template_choices)


@app.cell
def _(country_choices, mo, template_choices):
    mo.md(f"""
    ### Choices Overview

    - **Template choices**: {len(template_choices)} choices across {template_choices['list_name'].nunique()} lists
    - **Country choices extracted**: {len(country_choices)} choices
    - **Unique lists in countries**: {country_choices['list_name'].nunique() if len(country_choices) > 0 else 0}
    """)
    return


@app.cell
def _(mo):
    mo.md("""
    ### List Name Coverage Summary
    
    Analysis of choice list (list_name) compliance for each country form.
    """)
    return


@app.cell
def _(assets_df, country_choices, mo, pd, survey_df, template_choices):
    # Calculate comprehensive choices compliance metrics per country
    template_lists = set(template_choices['list_name'].dropna().unique())
    
    # Get questions with choices per country (from survey_df)
    select_questions_df = survey_df[
        survey_df['type'].notna() & 
        (survey_df['type'].str.startswith('select_one ') | 
         survey_df['type'].str.startswith('select_multiple '))
    ].copy()
    
    # Extract list_name from type column
    select_questions_df['list_name'] = select_questions_df['type'].str.replace('select_one ', '').str.replace('select_multiple ', '').str.strip()
    
    # Calculate metrics per survey
    choices_summary_records = []
    
    # Loop over asset_uid to ensure each project gets its own row (even if survey_name is duplicate)
    for _survey_asset_uid in country_choices['asset_uid'].unique():
        survey_data = country_choices[country_choices['asset_uid'] == _survey_asset_uid]
        _survey_name = survey_data.iloc[0]['survey_name']
        _country_code = survey_data.iloc[0]['country_code']
        
        # Get questions with choices for this survey
        survey_questions = select_questions_df[select_questions_df['asset_uid'] == _survey_asset_uid]
        
        # Get submissions count from assets_df
        _n_submissions = assets_df[assets_df['uid'] == _survey_asset_uid]['submission_count'].iloc[0]
        
        n_total_questions_with_choices = len(survey_questions)
        
        # Count questions using template list_names
        country_lists = set(survey_data['list_name'].dropna().unique())
        matched_lists = template_lists & country_lists
        n_questions_with_template_lists = len(survey_questions[survey_questions['list_name'].isin(matched_lists)])
        
        # Calculate percentages
        _match_pct = (n_questions_with_template_lists / n_total_questions_with_choices * 100) if n_total_questions_with_choices > 0 else 0
        _mismatch_pct = 100 - _match_pct
        
        choices_summary_records.append({
            'survey_name': _survey_name,
            'country_code': _country_code,
            'submissions': _n_submissions,
            'n_questions_with_choices': n_total_questions_with_choices,
            'n_questions_match_template': n_questions_with_template_lists,
            'n_questions_mismatch': n_total_questions_with_choices - n_questions_with_template_lists,
            'match_pct': round(_match_pct, 1),
            'mismatch_pct': round(_mismatch_pct, 1)
        })
    
    choices_summary_detailed = pd.DataFrame(choices_summary_records).sort_values('match_pct', ascending=False)
    
    # Display table
    display_choices = choices_summary_detailed[['survey_name', 'country_code', 'submissions', 'n_questions_with_choices', 
                                                  'n_questions_match_template', 'n_questions_mismatch',
                                                  'match_pct', 'mismatch_pct']].copy()
    display_choices.columns = [
        'Survey', 'Country', 'Submissions', 'Total Questions w/ Choices', 
        'Questions Match Template', 'Questions Mismatch',
        'Match %', 'Mismatch %'
    ]
    
    mo.ui.table(display_choices, selection=None, page_size=25)
    return


@app.cell
def _(mo):
    mo.md("""
    ### Analysis 1: List_name Correctness by Question Name
    
    Verifies if questions use the correct list_name according to template.
    For each matched question (by name), checks if the list_name matches template.
    """)
    return


@app.cell
def _(assets_df, mo, pd, select_questions_df, survey_df, template):
    # Get template select questions with list_name
    template_select_questions = template.survey[
        template.survey['type'].notna() & 
        (template.survey['type'].str.startswith('select_one ') | 
         template.survey['type'].str.startswith('select_multiple '))
    ].copy()
    
    template_select_questions['list_name'] = template_select_questions['type'].str.replace(
        'select_one ', '').str.replace('select_multiple ', '').str.strip()
    
    # Create mapping: question name -> list_name from template
    template_question_listname = template_select_questions.set_index('name')['list_name'].to_dict()
    
    # Analyze per project
    listname_correctness_records = []
    
    for _asset_uid in assets_df['uid']:
        _project_name = assets_df[assets_df['uid'] == _asset_uid]['name'].iloc[0]
        _country_code = assets_df[assets_df['uid'] == _asset_uid]['country_code_settings'].iloc[0]
        _n_submissions = assets_df[assets_df['uid'] == _asset_uid]['submission_count'].iloc[0]
        
        # Get project's select questions
        _project_questions = select_questions_df[select_questions_df['asset_uid'] == _asset_uid]
        
        _n_total_select = len(_project_questions)
        _n_correct_listname = 0
        _n_wrong_listname = 0
        _n_not_in_template = 0
        
        for _, _question in _project_questions.iterrows():
            _question_name = _question['name']
            _country_listname = _question['list_name']
            
            if _question_name in template_question_listname:
                # Question exists in template
                _template_listname = template_question_listname[_question_name]
                if _country_listname == _template_listname:
                    _n_correct_listname += 1
                else:
                    _n_wrong_listname += 1
            else:
                # Question name not in template
                _n_not_in_template += 1
        
        # Calculate percentage (only for matched questions)
        _n_matched_questions = _n_correct_listname + _n_wrong_listname
        _correct_pct = (_n_correct_listname / _n_matched_questions * 100) if _n_matched_questions > 0 else 0
        
        listname_correctness_records.append({
            'survey_name': _project_name,
            'country_code': _country_code,
            'submissions': _n_submissions,
            'n_total_select_questions': _n_total_select,
            'n_matched_questions': _n_matched_questions,
            'n_correct_listname': _n_correct_listname,
            'n_wrong_listname': _n_wrong_listname,
            'n_not_in_template': _n_not_in_template,
            'correct_listname_pct': round(_correct_pct, 1)
        })
    
    listname_correctness_df = pd.DataFrame(listname_correctness_records).sort_values(
        'correct_listname_pct', ascending=False)
    
    # Display table
    display_ln_correctness = listname_correctness_df[[
        'survey_name', 'country_code', 'submissions', 'n_total_select_questions',
        'n_matched_questions', 'n_correct_listname', 'n_wrong_listname', 
        'n_not_in_template', 'correct_listname_pct'
    ]].copy()
    display_ln_correctness.columns = [
        'Survey', 'Country', 'Submissions', 'Total Select Questions',
        'Matched Questions', 'Correct List_name', 'Wrong List_name',
        'Not in Template', 'Correct %'
    ]
    
    mo.ui.table(display_ln_correctness, selection=None, page_size=25)
    return


@app.cell
def _(mo):
    mo.md("""
    ### Analysis 2: Choice Modalities Comparison
    
    For list_names that exist in both template and country project, compares the actual choices (modalities).
    Identifies missing, extra, or modified choice options.
    """)
    return


@app.cell
def _(assets_df, country_choices, mo, pd, template_choices):
    # Analyze choice modalities per project and list_name
    modalities_comparison_records = []
    
    for _asset_uid in assets_df['uid']:
        _project_name = assets_df[assets_df['uid'] == _asset_uid]['name'].iloc[0]
        _country_code = assets_df[assets_df['uid'] == _asset_uid]['country_code_settings'].iloc[0]
        _n_submissions = assets_df[assets_df['uid'] == _asset_uid]['submission_count'].iloc[0]
        
        # Get project's choices
        _project_choices = country_choices[country_choices['asset_uid'] == _asset_uid]
        
        # Get unique list_names for this project
        _project_listsnames = _project_choices['list_name'].dropna().unique()
        
        for _list_name in _project_listsnames:
            # Check if list_name exists in template
            if _list_name not in template_choices['list_name'].values:
                continue  # Skip lists not in template
            
            # Get template choices for this list (template uses 'name' column)
            _template_list_choices = set(
                str(x) for x in template_choices[template_choices['list_name'] == _list_name]['name'].dropna().unique()
            )
            
            # Get country choices for this list (country uses 'choice_name' column)
            _country_list_choices = set(
                str(x) for x in _project_choices[_project_choices['list_name'] == _list_name]['choice_name'].dropna().unique()
            )
            
            # Compare
            _identical = _template_list_choices & _country_list_choices
            _missing = _template_list_choices - _country_list_choices
            _extra = _country_list_choices - _template_list_choices
            
            _n_identical = len(_identical)
            _n_missing = len(_missing)
            _n_extra = len(_extra)
            _n_template_total = len(_template_list_choices)
            
            # Calculate conformity percentage
            _conformity_pct = (_n_identical / _n_template_total * 100) if _n_template_total > 0 else 0
            
            modalities_comparison_records.append({
                'survey_name': _project_name,
                'country_code': _country_code,
                'submissions': _n_submissions,
                'list_name': _list_name,
                'n_template_choices': _n_template_total,
                'n_country_choices': len(_country_list_choices),
                'n_identical': _n_identical,
                'n_missing': _n_missing,
                'n_extra': _n_extra,
                'conformity_pct': round(_conformity_pct, 1),
                'missing_choices': ', '.join(sorted(_missing)) if _missing else '-',
                'extra_choices': ', '.join(sorted(_extra)) if _extra else '-'
            })
    
    modalities_comparison_df = pd.DataFrame(modalities_comparison_records).sort_values(
        ['survey_name', 'conformity_pct'], ascending=[True, False])
    
    return (modalities_comparison_df,)


@app.cell
def _(modalities_comparison_df, mo):
    mo.md("""
    #### Summary Table: Choice Modalities Conformity by Project and List_name
    
    Shows conformity metrics for each list_name in each project.
    """)
    return


@app.cell
def _(modalities_comparison_df, mo):
    # Display summary table
    display_modalities_summary = modalities_comparison_df[[
        'survey_name', 'country_code', 'submissions', 'list_name',
        'n_template_choices', 'n_country_choices', 'n_identical',
        'n_missing', 'n_extra', 'conformity_pct'
    ]].copy()
    display_modalities_summary.columns = [
        'Survey', 'Country', 'Submissions', 'List Name',
        'Template Choices', 'Country Choices', 'Identical',
        'Missing', 'Extra', 'Conformity %'
    ]
    
    mo.ui.table(display_modalities_summary, selection=None, page_size=25)
    return


@app.cell
def _(mo):
    mo.md("""
    #### Detailed Table: Non-Conforming Choice Lists
    
    Shows only list_names with differences (missing or extra choices).
    """)
    return


@app.cell
def _(modalities_comparison_df, mo):
    # Filter to show only non-conforming lists
    non_conforming = modalities_comparison_df[
        (modalities_comparison_df['n_missing'] > 0) | 
        (modalities_comparison_df['n_extra'] > 0)
    ].copy()
    
    if len(non_conforming) > 0:
        display_detailed = non_conforming[[
            'survey_name', 'country_code', 'list_name', 'conformity_pct',
            'n_missing', 'missing_choices', 'n_extra', 'extra_choices'
        ]].copy()
        display_detailed.columns = [
            'Survey', 'Country', 'List Name', 'Conformity %',
            'N Missing', 'Missing Choices', 'N Extra', 'Extra Choices'
        ]
        
        mo.ui.table(display_detailed, selection=None, page_size=25)
    else:
        mo.md("*All choice lists are 100% conforming - no differences found.*")
    return


@app.cell
def _(mo):
    mo.md("""
    ---
    ## 5. Constraints Compliance Analysis

    Analyzes whether question constraints (validation rules) match between template and country forms.
    **Only considers questions that have a constraint defined in the template.**
    """)
    return


@app.cell
def _(assets_df, mo, pd, survey_df, template):
    import re
    
    def _normalize_constraint(constraint):
        """Normalize whitespace in constraints for better comparison.
        
        Removes ALL whitespace to ensure constraints like '.>= 0' and '.>=0' 
        are treated as identical. This doesn't alter constraint logic.
        """
        if not constraint or constraint in ['', 'nan', 'None']:
            return ''
        # Remove ALL whitespace characters
        return re.sub(r'\s+', '', str(constraint))
    
    # Get template constraints (constraint column might be 'constraint' or similar)
    template_constraints = template.survey[['name', 'constraint']].copy()
    template_constraints = template_constraints.dropna(subset=['name'])
    
    # Get all template question names (for checking existence)
    # Note: question names are already normalized at source (whitespace stripped)
    template_question_names = set(template.survey['name'].dropna().unique())
    
    # Create mapping: question name -> constraint from template
    template_constraint_map = {}
    for _, _row in template_constraints.iterrows():
        _name = _row['name']
        _constraint = _row['constraint'] if pd.notna(_row['constraint']) else ''
        template_constraint_map[_name] = _normalize_constraint(_constraint)
    
    # Analyze per project
    constraint_compliance_records = []
    constraint_details_records = []
    constraint_not_in_template_records = []
    
    for _asset_uid in assets_df['uid']:
        _project_name = assets_df[assets_df['uid'] == _asset_uid]['name'].iloc[0]
        _country_code = assets_df[assets_df['uid'] == _asset_uid]['country_code_settings'].iloc[0]
        _n_submissions = assets_df[assets_df['uid'] == _asset_uid]['submission_count'].iloc[0]
        
        # Get project questions (APPLY SAME FILTER: exclude begin/end/note groups)
        _project_questions = survey_df[
            (survey_df['asset_uid'] == _asset_uid) &
            (survey_df['type'].notna()) &
            (~survey_df['type'].str.startswith(('begin', 'end', 'note'), na=False))
        ][['name', 'constraint']].copy()
        
        _n_total_questions = 0
        _n_matched_constraint = 0
        _n_mismatched_constraint = 0
        _n_not_in_template = 0
        
        for _, _q in _project_questions.iterrows():
            _q_name = _q['name']
            if pd.isna(_q_name):
                continue
            
            # Note: question names are already normalized at source (whitespace stripped)
            _country_constraint = _normalize_constraint(_q['constraint']) if pd.notna(_q['constraint']) else ''
            
            # Check if question exists in template (by name)
            if _q_name in template_question_names:
                # Question exists in template
                _template_constraint = template_constraint_map.get(_q_name, '')
                
                # Normalize empty constraints
                _template_constraint_norm = _template_constraint if _template_constraint != '' else ''
                _country_constraint_norm = _country_constraint if _country_constraint != '' else ''
                
                # Only count questions that have a constraint in the template
                if _template_constraint_norm != '':
                    _n_total_questions += 1
                    
                    if _template_constraint_norm == _country_constraint_norm:
                        _n_matched_constraint += 1
                        _status = 'Match'
                    else:
                        _n_mismatched_constraint += 1
                        _status = 'Mismatch'
                    
                    # Store details
                    constraint_details_records.append({
                        'asset_uid': _asset_uid,
                        'survey_name': _project_name,
                        'country_code': _country_code,
                        'question_name': _q_name,
                        'template_constraint': _template_constraint_norm,
                        'country_constraint': _country_constraint_norm,
                        'status': _status
                    })
            else:
                # Question truly not in template
                _n_not_in_template += 1
                
                # Store questions with constraints that are not in template
                if _country_constraint != '':
                    constraint_not_in_template_records.append({
                        'asset_uid': _asset_uid,
                        'survey_name': _project_name,
                        'country_code': _country_code,
                        'question_name': _q_name,
                        'country_constraint': _country_constraint
                    })
        
        # Calculate percentage
        _match_pct = (_n_matched_constraint / _n_total_questions * 100) if _n_total_questions > 0 else 0
        
        constraint_compliance_records.append({
            'asset_uid': _asset_uid,
            'survey_name': _project_name,
            'country_code': _country_code,
            'submissions': _n_submissions,
            'n_total_questions': _n_total_questions,
            'n_matched_constraint': _n_matched_constraint,
            'n_mismatched_constraint': _n_mismatched_constraint,
            'n_not_in_template': _n_not_in_template,
            'match_pct': round(_match_pct, 1)
        })
    
    constraint_compliance_df = pd.DataFrame(constraint_compliance_records).sort_values('match_pct', ascending=False)
    constraint_details_df = pd.DataFrame(constraint_details_records)
    constraint_not_in_template_df = pd.DataFrame(constraint_not_in_template_records)
    
    return (constraint_compliance_df, constraint_details_df, constraint_not_in_template_df)


@app.cell
def _(constraint_compliance_df, mo):
    mo.md("""
    ### Summary: Constraints Compliance by Project
    
    Shows constraint compliance for questions that **have a constraint defined in the template**.
    """)
    return


@app.cell
def _(constraint_compliance_df, mo):
    # Display summary table
    _display_constraint_summary = constraint_compliance_df[[
        'survey_name', 'asset_uid', 'country_code', 'submissions', 'n_total_questions',
        'n_matched_constraint', 'n_mismatched_constraint', 'n_not_in_template', 'match_pct'
    ]].copy()
    _display_constraint_summary.columns = [
        'Survey', 'Kobo UID', 'Country', 'Submissions', 'Questions w/ Constraint (Template)',
        'Matched Constraints', 'Mismatched Constraints', 'Not in Template', 'Match %'
    ]
    
    mo.ui.table(_display_constraint_summary, selection=None, page_size=25)
    return


@app.cell
def _(mo):
    mo.md("""
    ### Detailed View: Constraint Differences
    
    Filter by country and question name to see specific constraint differences.
    """)
    return


@app.cell
def _(constraint_details_df, mo):
    # Create filter dropdowns
    _projects_list = ['All'] + sorted(constraint_details_df['survey_name'].dropna().unique().tolist())
    _questions_list = ['All'] + sorted(constraint_details_df['question_name'].dropna().unique().tolist())
    
    project_filter = mo.ui.dropdown(
        options=_projects_list,
        value='All',
        label="Filter by Kobo Project"
    )
    
    question_filter = mo.ui.dropdown(
        options=_questions_list,
        value='All',
        label="Filter by Question Name"
    )
    
    status_filter = mo.ui.dropdown(
        options=['All', 'Match', 'Mismatch'],
        value='Mismatch',
        label="Filter by Status"
    )
    
    mo.hstack([project_filter, question_filter, status_filter])
    return (project_filter, question_filter, status_filter)


@app.cell
def _(constraint_details_df, mo, project_filter, question_filter, status_filter):
    # Apply filters
    _filtered_constraints = constraint_details_df.copy()
    
    if project_filter.value != 'All':
        _filtered_constraints = _filtered_constraints[_filtered_constraints['survey_name'] == project_filter.value]
    
    if question_filter.value != 'All':
        _filtered_constraints = _filtered_constraints[_filtered_constraints['question_name'] == question_filter.value]
    
    if status_filter.value != 'All':
        _filtered_constraints = _filtered_constraints[_filtered_constraints['status'] == status_filter.value]
    
    if len(_filtered_constraints) > 0:
        _display_constraints = _filtered_constraints[[
            'survey_name', 'asset_uid', 'country_code', 'question_name', 'status',
            'template_constraint', 'country_constraint'
        ]].copy()
        _display_constraints.columns = [
            'Survey', 'Kobo UID', 'Country', 'Question Name', 'Status',
            'Template Constraint', 'Country Constraint'
        ]
        
        _result = mo.vstack([
            mo.md(f"**{len(_filtered_constraints)} questions** matching filters"),
            mo.ui.table(_display_constraints, selection=None, page_size=25)
        ])
    else:
        _result = mo.md("*No questions match the selected filters*")
    
    _result
    return


@app.cell
def _(mo):
    mo.md("""
    ### Questions with Constraints Not in Template
    
    Shows country-specific questions that have constraints but don't exist in the template.
    These are custom questions added by individual country missions.
    """)
    return


@app.cell
def _(assets_df, constraint_not_in_template_df, mo):
    # Create project filter dropdown
    _projects_list = ['All'] + sorted(assets_df['name'].unique().tolist())
    
    project_constraint_filter = mo.ui.dropdown(
        options=_projects_list,
        value='All',
        label="Filter by Kobo Project"
    )
    
    project_constraint_filter
    return (project_constraint_filter,)


@app.cell
def _(constraint_not_in_template_df, mo, project_constraint_filter):
    # Apply filter
    _filtered_not_in_template = constraint_not_in_template_df.copy()
    
    if project_constraint_filter.value != 'All':
        _filtered_not_in_template = _filtered_not_in_template[
            _filtered_not_in_template['survey_name'] == project_constraint_filter.value
        ]
    
    if len(_filtered_not_in_template) > 0:
        _display_not_in_template = _filtered_not_in_template[[
            'survey_name', 'asset_uid', 'country_code', 'question_name', 'country_constraint'
        ]].copy()
        _display_not_in_template.columns = [
            'Survey', 'Kobo UID', 'Country', 'Question Name', 'Constraint'
        ]
        
        _result_not_in_template = mo.vstack([
            mo.md(f"**{len(_filtered_not_in_template)} questions** with constraints not in template"),
            mo.ui.table(_display_not_in_template, selection=None, page_size=25)
        ])
    else:
        _result_not_in_template = mo.md("*No questions with constraints found outside template for selected project*")
    
    _result_not_in_template
    return


@app.cell
def _(mo):
    mo.md("""
    ---
    
    ## Constraint Compliance Visualizations
    
    Visual summaries of constraint compliance across all projects, showing the funnel from total questions to matched constraints.
    """)
    return


@app.cell
def _(constraint_compliance_df, constraint_not_in_template_df, pd, survey_df):
    """Calculate metrics for constraint compliance visualizations."""
    
    # For each project, get:
    # 1. Total questions count (from survey_df, excluding begin/end/note)
    # 2. Questions with matching constraint (n_matched_constraint)
    # 3. Questions with mismatched constraint (n_mismatched_constraint)
    # 4. Questions with constraint NOT in template (from constraint_not_in_template_df)
    # 5. Questions without constraint or in template without constraint (the rest)
    
    viz_data = []
    
    for _, row in constraint_compliance_df.iterrows():
        asset_uid = row['asset_uid']
        survey_name = row['survey_name']
        country_code = row['country_code']
        
        # Total questions in project (SAME FILTER AS TEMPLATE: excluding groups/notes)
        project_questions = survey_df[
            (survey_df['asset_uid'] == asset_uid) &
            (survey_df['type'].notna()) &
            (~survey_df['type'].str.startswith(('begin', 'end', 'note'), na=False))
        ]
        total_questions = len(project_questions)
        
        # Questions with matching constraint
        questions_matched_constraint = row['n_matched_constraint']
        
        # Questions with mismatched constraint
        questions_mismatched_constraint = row['n_mismatched_constraint']
        
        # Questions with constraint but NOT in template (country-specific with constraint)
        questions_with_constraint_not_in_template = len(
            constraint_not_in_template_df[constraint_not_in_template_df['asset_uid'] == asset_uid]
        )
        
        # Questions without constraint (the rest)
        questions_without_constraint = (
            total_questions - 
            questions_matched_constraint - 
            questions_mismatched_constraint - 
            questions_with_constraint_not_in_template
        )
        
        viz_data.append({
            'asset_uid': asset_uid,
            'survey_name': survey_name,
            'country_code': country_code,
            'total_questions': total_questions,
            'questions_matched_constraint': questions_matched_constraint,
            'questions_mismatched_constraint': questions_mismatched_constraint,
            'questions_constraint_not_in_template': questions_with_constraint_not_in_template,
            'questions_no_constraint': questions_without_constraint
        })
    
    viz_df = pd.DataFrame(viz_data)
    
    # Calculate global metrics (only for questions with constraint in template)
    global_total = viz_df['questions_matched_constraint'].sum() + viz_df['questions_mismatched_constraint'].sum()
    global_matched = viz_df['questions_matched_constraint'].sum()
    global_compliance_pct = round((global_matched / global_total * 100), 1) if global_total > 0 else 0
    
    return (global_compliance_pct, global_matched, global_total, viz_df)


@app.cell
def _(global_compliance_pct, global_matched, global_total, mo):
    """Display global constraint compliance KPI."""
    
    mo.md(f"""
    ### 📊 Global Constraint Compliance
    
    <div style="text-align: center; padding: 20px; background-color: #f0f8ff; border-radius: 10px; margin: 20px 0;">
        <h2 style="color: #2c3e50; margin: 10px 0;">{global_compliance_pct}%</h2>
        <p style="color: #555; font-size: 16px;">
            <strong>{global_matched:,}</strong> out of <strong>{global_total:,}</strong> questions with constraints match the template
        </p>
        <p style="color: #777; font-size: 14px; margin-top: 10px;">
            For questions that exist in both template and country forms with a constraint defined in the template
        </p>
    </div>
    """)
    return


@app.cell
def _(mo, px, viz_df):
    """Create horizontal stacked bar chart showing constraint matching for questions found in template."""
    
    # Prepare data for stacked bar chart
    viz_plot_df = viz_df.copy()
    
    # Sort by country code for easier reading
    viz_plot_df = viz_plot_df.sort_values('country_code')
    
    # Create figure with stacked bars (2 categories only: matched vs mismatched)
    fig = px.bar(
        viz_plot_df,
        y='survey_name',
        x=['questions_matched_constraint', 'questions_mismatched_constraint'],
        orientation='h',
        title='Validation rules (constraints): comparison with template for matched questions',
        labels={
            'value': 'Number of questions',
            'survey_name': 'Project',
            'variable': 'Category'
        },
        color_discrete_map={
            'questions_matched_constraint': '#3498db',  # Blue - same constraint
            'questions_mismatched_constraint': '#95a5a6',  # Gray - different constraint
        },
        height=max(500, len(viz_plot_df) * 30)
    )
    
    # Rename legend labels
    newnames = {
        'questions_matched_constraint': 'Same validation rule',
        'questions_mismatched_constraint': 'Different validation rule'
    }
    fig.for_each_trace(lambda t: t.update(name=newnames.get(t.name, t.name)))
    
    # Update layout
    fig.update_layout(
        xaxis_title='Number of questions',
        yaxis_title='',
        legend_title='',
        barmode='stack',
        font=dict(size=12),
        plot_bgcolor='white',
        showlegend=True,
        legend=dict(
            orientation='h',
            yanchor='bottom',
            y=1.02,
            xanchor='right',
            x=1
        )
    )
    
    # Add grid
    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='lightgray')
    
    mo.ui.plotly(fig)
    return fig


@app.cell
def _(mo, px, viz_df):
    """Create percentage-based bar chart showing constraint matching proportions."""
    
    # Prepare data for percentage view
    viz_pct_df = viz_df.copy()
    
    # Calculate percentages
    viz_pct_df['total_with_constraint'] = (
        viz_pct_df['questions_matched_constraint'] + 
        viz_pct_df['questions_mismatched_constraint']
    )
    viz_pct_df['pct_matched'] = (
        (viz_pct_df['questions_matched_constraint'] / viz_pct_df['total_with_constraint'] * 100)
        .fillna(0)
        .round(1)
    )
    viz_pct_df['pct_mismatched'] = 100 - viz_pct_df['pct_matched']
    
    # Sort by percentage matched (descending)
    viz_pct_df = viz_pct_df.sort_values('pct_matched', ascending=True)
    
    # Create figure with percentage bars
    fig_pct = px.bar(
        viz_pct_df,
        y='survey_name',
        x=['pct_matched', 'pct_mismatched'],
        orientation='h',
        title='Constraints comparison: proportion of questions with same validation rules as template',
        labels={
            'value': 'Percentage (%)',
            'survey_name': 'Project',
            'variable': 'Category'
        },
        color_discrete_map={
            'pct_matched': '#3498db',  # Blue
            'pct_mismatched': '#95a5a6',  # Gray
        },
        height=max(500, len(viz_pct_df) * 30),
        text_auto=False
    )
    
    # Rename legend labels
    newnames_pct = {
        'pct_matched': 'Same validation rule',
        'pct_mismatched': 'Different validation rule'
    }
    fig_pct.for_each_trace(lambda t: t.update(name=newnames_pct.get(t.name, t.name)))
    
    # Add text annotations with absolute numbers and percentages
    for idx, _row in viz_pct_df.iterrows():
        # Add matched count on the matched bar
        if _row['pct_matched'] > 5:  # Only show if bar is wide enough
            fig_pct.add_annotation(
                x=_row['pct_matched'] / 2,
                y=_row['survey_name'],
                text=f"{_row['pct_matched']:.0f}% ({int(_row['questions_matched_constraint'])})",
                showarrow=False,
                font=dict(color='white', size=10, family='Arial'),
                xanchor='center'
            )
        
        # Add mismatched count on the mismatched bar
        if _row['pct_mismatched'] > 5:  # Only show if bar is wide enough
            fig_pct.add_annotation(
                x=_row['pct_matched'] + _row['pct_mismatched'] / 2,
                y=_row['survey_name'],
                text=f"{_row['pct_mismatched']:.0f}% ({int(_row['questions_mismatched_constraint'])})",
                showarrow=False,
                font=dict(color='white', size=10, family='Arial'),
                xanchor='center'
            )
        
        # Add total count at the end of the bar
        total_matched = int(_row['total_with_constraint'])
        fig_pct.add_annotation(
            x=105,  # Position slightly to the right of the 100% mark
            y=_row['survey_name'],
            text=f"<b>{total_matched}</b>",
            showarrow=False,
            font=dict(color='#2c3e50', size=11, family='Arial'),
            xanchor='left'
        )
    
    # Update layout
    fig_pct.update_layout(
        xaxis_title='Percentage (%)',
        yaxis_title='',
        legend_title='',
        barmode='stack',
        font=dict(size=12),
        plot_bgcolor='white',
        showlegend=True,
        legend=dict(
            orientation='h',
            yanchor='bottom',
            y=1.02,
            xanchor='right',
            x=1
        ),
        xaxis=dict(range=[0, 115])  # Extended to make room for annotations
    )
    
    # Add grid
    fig_pct.update_xaxes(showgrid=True, gridwidth=1, gridcolor='lightgray')
    
    mo.ui.plotly(fig_pct)
    return fig_pct


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
