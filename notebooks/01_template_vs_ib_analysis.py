"""MSNA 2025 Template vs Indicator Bank Analysis.

Analysis of question code mismatches between Kobo form template and indicator bank
to identify gaps in HQ process and improve template standardization.
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
    import sys

    # Add project root to path
    project_root = Path.cwd()
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    from src.template import load_template
    from src.indicator_bank import load_indicator_bank

    mo.md("""
    # MSNA 2025: Template vs Indicator Bank Analysis

    **Objective**: Identify mismatches between Kobo form template and indicator bank 
    to improve HQ standardization process.
    """)
    return load_indicator_bank, load_template, mo, pd, px


@app.cell
def _(load_indicator_bank, load_template, mo):
    # Load data
    template = load_template()
    indicator_bank = load_indicator_bank()

    # Define Kobo technical elements to exclude from analysis
    kobo_technical_types = ['begin_group', 'end_group', 'begin_repeat', 'end_repeat']
    kobo_metadata_names = ['audit', 'start', 'end', 'today', 'deviceid']
    
    # Extract question codes, filtering out Kobo structural elements and metadata
    all_template_names = template.survey[
        (template.survey['name'].notna()) & 
        (~template.survey['type'].isin(kobo_technical_types)) &
        (~template.survey['name'].isin(kobo_metadata_names))
    ]['name'].tolist()
    
    template_questions = set(all_template_names)
    ib_questions = set(indicator_bank.get_question_codes())

    # Calculate matches
    matched = template_questions & ib_questions
    in_template_not_ib = template_questions - ib_questions
    in_ib_not_template = ib_questions - template_questions

    mo.md("## Match Analysis")
    return (
        ib_questions,
        in_ib_not_template,
        in_template_not_ib,
        indicator_bank,
        kobo_metadata_names,
        kobo_technical_types,
        matched,
        template,
        template_questions,
    )


@app.cell
def _(
    ib_questions,
    in_ib_not_template,
    in_template_not_ib,
    matched,
    pd,
    template_questions,
):
    # Global mismatch statistics
    match_rate_ib = len(matched) / len(ib_questions) * 100
    match_rate_template = len(matched) / len(template_questions) * 100

    # Create clear summary table
    summary_table = pd.DataFrame({
        'Document': ['Template', 'Indicator Bank'],
        'Total Questions': [len(template_questions), len(ib_questions)],
        'Matched': [len(matched), len(matched)],
        'Matched %': [f'{match_rate_template:.1f}%', f'{match_rate_ib:.1f}%'],
        'Not Matched': [len(in_template_not_ib), len(in_ib_not_template)],
        'Not Matched %': [f'{len(in_template_not_ib)/len(template_questions)*100:.1f}%', 
                          f'{len(in_ib_not_template)/len(ib_questions)*100:.1f}%']
    })
    return match_rate_ib, match_rate_template, summary_table


@app.cell
def _(mo, summary_table):
    mo.ui.table(summary_table, selection=None)
    return


@app.cell
def _(in_template_not_ib, kobo_metadata_names, kobo_technical_types, mo, pd, template):
    # Prepare mismatch export - questions in template but not in IB
    base_cols = ['name', 'type', 'theme', 'module']
    
    label_col_export = None
    for col_export in template.survey.columns:
        if 'label' in col_export.lower() and 'english' in col_export.lower():
            label_col_export = col_export
            break
    
    cols_to_select = base_cols + ([label_col_export] if label_col_export else [])
    
    mismatch_export = template.survey[
        (template.survey['name'].notna()) & 
        (~template.survey['type'].isin(kobo_technical_types)) &
        (~template.survey['name'].isin(kobo_metadata_names)) &
        (template.survey['name'].isin(in_template_not_ib))
    ][cols_to_select].copy()
    
    new_col_names = ['Question Code', 'Type', 'Theme', 'Module']
    if label_col_export:
        new_col_names.append('Label')
    mismatch_export.columns = new_col_names
    
    mismatch_button = mo.download(
        data=mismatch_export.to_csv(index=False).encode('utf-8'),
        filename='template_questions_not_in_ib.csv',
        label=f'Download Mismatches ({len(mismatch_export)} questions)',
        mimetype='text/csv'
    )
    
    return mismatch_button, mismatch_export


@app.cell
def _(mismatch_button, mo):
    mo.vstack([
        mo.md("""
        ## Download Mismatch Data
        
        Questions in the template but not in the Indicator Bank.
        """),
        mismatch_button
    ])
    return


@app.cell
def _(in_ib_not_template, in_template_not_ib):
    # Fuzzy matching analysis to detect near-matches (typos, plurals, etc.)
    from rapidfuzz import fuzz, process
    
    # Find close matches between template-only and IB-only question names
    close_matches = []
    
    for template_name in in_template_not_ib:
        # Find best matches in IB
        matches = process.extract(
            template_name, 
            in_ib_not_template, 
            scorer=fuzz.ratio,
            limit=3  # Top 3 matches
        )
        
        for ib_name, score, _ in matches:
            if score >= 60:  # Minimum threshold to consider
                close_matches.append({
                    'Template Name': template_name,
                    'IB Name': ib_name,
                    'Similarity Score': score,
                    'Length Diff': abs(len(template_name) - len(ib_name))
                })
    
    # Sort by similarity score descending
    close_matches_sorted = sorted(close_matches, key=lambda x: x['Similarity Score'], reverse=True)
    
    return close_matches_sorted, fuzz, process


@app.cell
def _(mo):
    # Create interactive slider for similarity threshold
    similarity_threshold = mo.ui.slider(
        start=70,
        stop=100,
        step=1,
        value=85,
        label="Similarity Threshold (%)",
        show_value=True
    )
    
    return (similarity_threshold,)


@app.cell
def _(close_matches_sorted, mo, pd, similarity_threshold):
    # Filter matches based on threshold
    filtered_matches = [
        match for match in close_matches_sorted 
        if match['Similarity Score'] >= similarity_threshold.value
    ]
    
    near_matches_df = pd.DataFrame(filtered_matches)
    
    mo.vstack([
        mo.md(f"""
        ## Near-Match Detection (Potential Typos & Variants)
        
        Analysis of question names that are similar but not identical between Template and IB.
        This helps identify potential typos, plurals, or naming inconsistencies.
        
        **Found {len(near_matches_df)} potential near-matches at current threshold.**
        
        Adjust the similarity threshold to fine-tune detection:
        """),
        similarity_threshold,
        mo.ui.table(near_matches_df, selection=None) if len(near_matches_df) > 0 else mo.md("*No near-matches found at this threshold.*")
    ])
    return (near_matches_df,)


@app.cell
def _(kobo_metadata_names, kobo_technical_types, matched, mo, px, template):
    # Match/mismatch breakdown by question type
    # Get all questions with their types, filtering out Kobo structural elements and metadata
    template_with_type = template.survey[
        (template.survey['name'].notna()) & 
        (~template.survey['type'].isin(kobo_technical_types)) &
        (~template.survey['name'].isin(kobo_metadata_names))
    ][['name', 'type']].copy()

    # Classify each question
    template_with_type['match_status'] = template_with_type['name'].apply(
        lambda x: 'Matched' if x in matched else 'Not in IB'
    )

    # Count by type and status
    type_analysis = template_with_type.groupby(['type', 'match_status']).size().reset_index(name='count')
    type_pivot = type_analysis.pivot(index='type', columns='match_status', values='count').fillna(0).astype(int)

    # Calculate totals and percentages
    type_pivot['Total'] = type_pivot.sum(axis=1)
    if 'Matched' in type_pivot.columns:
        type_pivot['Match %'] = (type_pivot['Matched'] / type_pivot['Total'] * 100).round(1)
    else:
        type_pivot['Match %'] = 0.0

    # Sort by mismatch descending (questions not in IB at the top)
    if 'Not in IB' in type_pivot.columns:
        type_pivot = type_pivot.sort_values('Not in IB', ascending=False).reset_index()
    else:
        type_pivot = type_pivot.sort_values('Total', ascending=False).reset_index()

    # Prepare data for horizontal barplot (all types, not limited to top 15)
    type_plot_data = type_pivot.melt(
        id_vars=['type', 'Total', 'Match %'],
        value_vars=[col for col in type_pivot.columns if col in ['Matched', 'Not in IB']],
        var_name='Status',
        value_name='Count'
    )

    fig_type = px.bar(
        type_plot_data,
        x='Count',
        y='type',
        color='Status',
        orientation='h',
        text='Count',
        title='Template Question Names: Match vs Mismatch with Indicator Bank by Question Type',
        barmode='stack',
        color_discrete_map={
            'Matched': '#2ecc71',
            'Not in IB': '#e74c3c'
        },
        hover_data=['Match %']
    )
    fig_type.update_traces(texttemplate='%{text}', textposition='inside')
    fig_type.update_layout(height=800, yaxis={'categoryorder': 'total ascending'})

    mo.md("""
    ## Match Analysis by Question Type

    Analysis of template question names compared to Indicator Bank, grouped by question type.
    Kobo structural elements (begin_group, end_group, begin_repeat, end_repeat) are excluded.
    Sorted by highest mismatch count.
    """)

    return fig_type, type_pivot


@app.cell
def _(fig_type, mo, type_pivot):
    mo.vstack([
        mo.ui.table(type_pivot, selection=None),
        mo.ui.plotly(fig_type)
    ])
    return


@app.cell
def _(in_ib_not_template, indicator_bank, matched, mo, pd):
    # Tier analysis
    ib_data = indicator_bank.data

    # Get tier for matched and non-matched questions
    tier_analysis = []

    for tier in ['1', '2', '3']:
        tier_questions = ib_data[ib_data['Tier (1, 2 or 3)'].astype(str) == tier]
        tier_question_codes = set(tier_questions['Question code'].dropna())

        tier_matched = tier_question_codes & matched
        tier_not_matched = tier_question_codes & in_ib_not_template

        tier_analysis.append({
            'Tier': f'Tier {tier}',
            'Total': len(tier_question_codes),
            'Matched': len(tier_matched),
            'Not in Template': len(tier_not_matched),
            'Match Rate (%)': len(tier_matched) / len(tier_question_codes) * 100 if len(tier_question_codes) > 0 else 0
        })

    tier_df = pd.DataFrame(tier_analysis)
    
    # Get Tier 1 questions not in template
    tier1_not_in_template = ib_data[
        (ib_data['Tier (1, 2 or 3)'].astype(str) == '1') &
        (ib_data['Question code'].isin(in_ib_not_template))
    ][['Question code', 'Sector/Theme', 'Module', 'Indicator']].copy()

    mo.md("""
    ## Analysis by Tier

    Breakdown of question matches by priority tier (1=critical, 2=important, 3=optional).
    """)
    return ib_data, tier1_not_in_template, tier_df


@app.cell
def _(mo, tier1_not_in_template, tier_df):
    mo.vstack([
        mo.ui.table(tier_df, selection=None),
        mo.md(f"""
        ### Tier 1 Questions Not in Template ({len(tier1_not_in_template)} critical questions)
        
        These critical questions are missing from the template.
        """),
        mo.ui.table(tier1_not_in_template, selection=None)
    ])
    return


@app.cell
def _(ib_data, in_ib_not_template, matched, pd):
    # Theme analysis
    theme_analysis = []

    for theme in ib_data['Sector/Theme'].dropna().unique():
        theme_questions = ib_data[ib_data['Sector/Theme'] == theme]
        theme_question_codes = set(theme_questions['Question code'].dropna())

        theme_matched = theme_question_codes & matched
        theme_not_matched = theme_question_codes & in_ib_not_template

        theme_analysis.append({
            'Theme': theme,
            'Total': len(theme_question_codes),
            'Matched': len(theme_matched),
            'Not in Template': len(theme_not_matched),
            'Match Rate (%)': len(theme_matched) / len(theme_question_codes) * 100 if len(theme_question_codes) > 0 else 0
        })

    theme_df = pd.DataFrame(theme_analysis).sort_values('Not in Template', ascending=False)
    return (theme_df,)


@app.cell
def _(mo, px, theme_df):
    # Theme visualization - top 10 themes with most mismatches
    theme_top10 = theme_df.head(10)

    fig_theme = px.bar(
        theme_top10,
        x='Not in Template',
        y='Theme',
        orientation='h',
        text='Not in Template',
        title='Top 10 Themes with Most Questions Missing from Template',
        color='Match Rate (%)',
        color_continuous_scale='RdYlGn'
    )
    fig_theme.update_traces(texttemplate='%{text}', textposition='outside')
    fig_theme.update_layout(height=500, yaxis={'categoryorder': 'total ascending'})

    mo.vstack([
        mo.md("""
        ## Analysis by Theme

        Mismatch breakdown by sector/theme - sorted by highest number of missing questions.
        """),
        mo.ui.table(theme_df, selection=None)
    ])
    return (fig_theme,)


@app.cell
def _(fig_theme, mo):
    mo.ui.plotly(fig_theme)
    return


@app.cell
def _(ib_data, in_ib_not_template, matched, pd):
    # Module analysis
    module_analysis = []

    for module in ib_data['Module'].dropna().unique():
        module_questions = ib_data[ib_data['Module'] == module]
        module_question_codes = set(module_questions['Question code'].dropna())

        module_matched = module_question_codes & matched
        module_not_matched = module_question_codes & in_ib_not_template

        module_theme = module_questions['Sector/Theme'].iloc[0] if len(module_questions) > 0 else 'Unknown'

        module_analysis.append({
            'Module': module,
            'Theme': module_theme,
            'Total': len(module_question_codes),
            'Matched': len(module_matched),
            'Not in Template': len(module_not_matched),
            'Match Rate (%)': len(module_matched) / len(module_question_codes) * 100 if len(module_question_codes) > 0 else 0
        })

    module_df = pd.DataFrame(module_analysis).sort_values('Not in Template', ascending=False)
    return (module_df,)


@app.cell
def _(mo, module_df, px):
    # Module visualization - top 15 modules with most mismatches
    module_top15 = module_df.head(15)

    fig_module = px.bar(
        module_top15,
        x='Not in Template',
        y='Module',
        orientation='h',
        text='Not in Template',
        title='Top 15 Modules with Most Questions Missing from Template',
        color='Theme',
        hover_data=['Total', 'Matched', 'Match Rate (%)']
    )
    fig_module.update_traces(texttemplate='%{text}', textposition='outside')
    fig_module.update_layout(height=600, yaxis={'categoryorder': 'total ascending'})

    mo.vstack([
        mo.md("""
        ## Analysis by Module

        Detailed breakdown by module - showing theme association and match rates.
        """),
        mo.ui.table(module_df, selection=None)
    ])
    return (fig_module,)


@app.cell
def _(fig_module, mo):
    mo.ui.plotly(fig_module)
    return


@app.cell
def _(ib_data, matched, pd, template):
    # Theme/Module mismatch analysis for matched questions
    mismatch_analysis = []
    
    for qcode_mismatch in matched:
        tmpl_row = template.survey[template.survey['name'] == qcode_mismatch]
        if len(tmpl_row) == 0:
            continue
            
        template_theme = tmpl_row['theme'].iloc[0] if pd.notna(tmpl_row['theme'].iloc[0]) else None
        template_module = tmpl_row['module'].iloc[0] if 'module' in tmpl_row.columns and pd.notna(tmpl_row['module'].iloc[0]) else None
        
        ind_row = ib_data[ib_data['Question code'] == qcode_mismatch]
        if len(ind_row) == 0:
            continue
            
        ib_theme = ind_row['Sector/Theme'].iloc[0] if pd.notna(ind_row['Sector/Theme'].iloc[0]) else None
        ib_module = ind_row['Module'].iloc[0] if pd.notna(ind_row['Module'].iloc[0]) else None
        
        theme_mismatch = (template_theme != ib_theme) and (template_theme is not None) and (ib_theme is not None)
        module_mismatch = (template_module != ib_module) and (template_module is not None) and (ib_module is not None)
        
        if theme_mismatch or module_mismatch:
            mismatch_analysis.append({
                'Question Code': qcode_mismatch,
                'Template Theme': template_theme,
                'IB Theme': ib_theme,
                'Theme Match': 'Yes' if not theme_mismatch else 'No',
                'Template Module': template_module,
                'IB Module': ib_module,
                'Module Match': 'Yes' if not module_mismatch else 'No'
            })
    
    mismatch_df = pd.DataFrame(mismatch_analysis)
    return (mismatch_df,)


@app.cell
def _(mismatch_df, mo):
    mo.vstack([
        mo.md(f"""
        ## Theme & Module Naming Mismatches
        
        Analysis of matched questions with different theme/module names between template and IB.
        Found {len(mismatch_df)} questions with naming inconsistencies.
        """),
        mo.ui.table(mismatch_df, selection=None)
    ])
    return


@app.cell
def _(ib_data, pd, template):
    # Theme/Module consistency check
    template_survey = template.survey
    template_themes = set(template_survey['theme'].dropna().unique())
    template_modules = set(template_survey['module'].dropna().unique()) if 'module' in template_survey.columns else set()

    ib_themes = set(ib_data['Sector/Theme'].dropna().unique())
    ib_modules = set(ib_data['Module'].dropna().unique())

    consistency_data = {
        'Metric': [
            'Unique themes in Template',
            'Unique themes in IB',
            'Unique modules in Template',
            'Unique modules in IB',
        ],
        'Count': [
            len(template_themes),
            len(ib_themes),
            len(template_modules),
            len(ib_modules),
        ]
    }

    consistency_df = pd.DataFrame(consistency_data)
    return (consistency_df,)


@app.cell
def _(consistency_df, mo):
    mo.ui.table(consistency_df, selection=None)
    return


@app.cell
def _(ib_data, matched, pd, template):
    # Constraint and Skip Logic analysis for matched questions
    skip_logic_analysis = []
    constraint_analysis = []
    
    for qcode_logic in matched:
        tpl_row = template.survey[template.survey['name'] == qcode_logic]
        if len(tpl_row) == 0:
            continue
            
        template_relevant = tpl_row['relevant'].iloc[0] if 'relevant' in tpl_row.columns else None
        template_constraint = tpl_row['constraint'].iloc[0] if 'constraint' in tpl_row.columns else None
        
        template_has_relevant = pd.notna(template_relevant) and str(template_relevant).strip() != ''
        template_has_constraint = pd.notna(template_constraint) and str(template_constraint).strip() != ''
        
        ib_row_logic = ib_data[ib_data['Question code'] == qcode_logic]
        if len(ib_row_logic) == 0:
            continue
        
        # Get skip logic from IB
        ib_skip_logic = None
        for col_logic in ['Subset / Skip logic', 'Skip logic', 'Subset', 'Skip Logic']:
            if col_logic in ib_row_logic.columns:
                ib_skip_logic = ib_row_logic[col_logic].iloc[0]
                break
        
        ib_constraint = ib_row_logic['Constraint'].iloc[0] if 'Constraint' in ib_row_logic.columns else None
        
        ib_has_skip_logic = pd.notna(ib_skip_logic) and str(ib_skip_logic).strip() != ''
        ib_has_constraint = pd.notna(ib_constraint) and str(ib_constraint).strip() != ''
        
        skip_logic_missing = ib_has_skip_logic and not template_has_relevant
        constraint_missing = ib_has_constraint and not template_has_constraint
        
        # Add to skip logic analysis
        if skip_logic_missing:
            skip_logic_analysis.append({
                'Question Code': qcode_logic,
                'IB Skip Logic': str(ib_skip_logic) if ib_has_skip_logic else '',
                'Template Relevant': str(template_relevant) if template_has_relevant else 'EMPTY'
            })
        
        # Add to constraint analysis
        if constraint_missing:
            constraint_analysis.append({
                'Question Code': qcode_logic,
                'IB Constraint': str(ib_constraint) if ib_has_constraint else '',
                'Template Constraint': str(template_constraint) if template_has_constraint else 'EMPTY'
            })
    
    skip_logic_df = pd.DataFrame(skip_logic_analysis)
    constraint_df = pd.DataFrame(constraint_analysis)
    
    return constraint_df, skip_logic_df


@app.cell
def _(constraint_df, mo, skip_logic_df):
    mo.vstack([
        mo.md(f"""
        ## Constraint & Skip Logic Mismatches
        
        Analysis of matched questions where IB has constraint/skip logic but template is empty.
        
        ### Skip Logic / Relevant Field Analysis
        
        **{len(skip_logic_df)}** questions where IB has skip logic but template relevant field is empty.
        """),
        mo.ui.table(skip_logic_df, selection=None),
        mo.md(f"""
        ### Constraint Field Analysis
        
        **{len(constraint_df)}** questions where IB has constraint but template constraint field is empty.
        """),
        mo.ui.table(constraint_df, selection=None)
    ])
    return


if __name__ == "__main__":
    app.run()
