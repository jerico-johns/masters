import streamlit as st
import requests
import pandas as pd
import numpy as np
import unicodedata

# Map ESPN API names to names used in masters_picks.csv
NAME_OVERRIDES = {
    'José María Olazábal': 'Jose Maria Olazabal',
    'Ludvig Åberg': 'Ludvig Aberg',
    'Nicolai Højgaard': 'Nicolai Hojgaard',
    'Rasmus Højgaard': 'Rasmus Hojgaard',
    'Ángel Cabrera': 'Angel Cabrera',
    'Sergio García': 'Sergio Garcia',
    'Sami Välimäki': 'Sami Valimaki',
    'Byeong Hun An': 'Byeong-Hun An',
    'Josele Ballester': 'Jose Luis Ballester',
}

def _normalize_name(name):
    """Strip accents and normalize unicode to ASCII for name matching."""
    if name in NAME_OVERRIDES:
        return NAME_OVERRIDES[name]
    # Strip accents as a fallback for names not in overrides
    nfkd = unicodedata.normalize('NFKD', name)
    return ''.join(c for c in nfkd if not unicodedata.combining(c))

# Masters Sunday dates by year (used to fetch the correct tournament from ESPN)
MASTERS_DATES = {
    2024: '20240414',
    2025: '20250413',
    2026: '20260412',
}

def get_masters_scores(year=None):
    url = 'https://site.api.espn.com/apis/site/v2/sports/golf/pga/scoreboard'
    params = {}
    if year and year in MASTERS_DATES:
        params['dates'] = MASTERS_DATES[year]
    response = requests.get(url, params=params)
    if response.status_code != 200:
        st.error(f"Failed to retrieve ESPN scores. Status code: {response.status_code}")
        return pd.DataFrame(columns=['golfer_name', 'score'])

    data = response.json()
    events = data.get('events', [])
    if not events:
        st.error("No active golf event found on ESPN.")
        return pd.DataFrame(columns=['golfer_name', 'score'])

    competition = events[0]['competitions'][0]
    competitors = competition['competitors']
    current_round = competition.get('status', {}).get('period', 1)

    def _parse_round(display_val):
        """Parse a round score display value to int, or None if not played."""
        if display_val in ('-', '--', None):
            return None
        if display_val == 'E':
            return 0
        return int(display_val.replace('+', ''))

    # Identify cut players and collect round scores from active players
    player_data = []
    active_round_scores = {}  # {round_num: [scores]}
    for player in competitors:
        name = _normalize_name(player['athlete']['fullName'])
        score_str = player.get('score', 'E')
        score = 0 if score_str == 'E' else int(score_str.replace('+', ''))
        linescores = player.get('linescores', [])

        is_cut = current_round >= 3 and any(ls.get('displayValue') == '-' for ls in linescores)
        player_data.append({'name': name, 'score': score, 'is_cut': is_cut, 'linescores': linescores})

        if not is_cut:
            for ls in linescores:
                rd = ls.get('period')
                val = _parse_round(ls.get('displayValue'))
                if rd and rd <= 4 and val is not None:
                    active_round_scores.setdefault(rd, []).append(val)

    # For each round after the cut (R3, R4), find the worst score among active players
    worst_by_round = {}
    for rd, scores in active_round_scores.items():
        worst_by_round[rd] = max(scores)

    # Apply cut penalty: for each missed round, add the worst active score
    # A cut player misses any round that (a) has a "-" linescore or
    # (b) exists in active_round_scores but is absent from their linescores
    rows = []
    for p in player_data:
        score = p['score']
        if p['is_cut']:
            linescore_rounds = set()
            for ls in p['linescores']:
                rd = ls.get('period')
                if rd:
                    linescore_rounds.add(rd)
                if ls.get('displayValue') == '-' and rd in worst_by_round:
                    score += worst_by_round[rd]
            # Also penalize for rounds with no linescore entry at all
            for rd, worst in worst_by_round.items():
                if rd not in linescore_rounds and rd in (3, 4):
                    score += worst
        # Determine current hole from the current round's hole-by-hole linescores
        current_ls = next((ls for ls in p['linescores'] if ls.get('period') == current_round), {})
        hole_scores = current_ls.get('linescores', [])
        if p['is_cut']:
            thru = 'CUT'
        elif current_ls.get('displayValue') == '-':
            thru = ''  # hasn't teed off yet
        elif len(hole_scores) >= 18:
            thru = 'F'
        elif len(hole_scores) > 0:
            thru = str(len(hole_scores))
        else:
            thru = ''
        rows.append({'golfer_name': p['name'], 'score': score, 'thru': thru})

    return pd.DataFrame(rows)

def calculate_top_n(row, n):
    scores = []
    for col in ['tier_1_1_score', 'tier_1_2_score', 'tier_1_3_score',
                'tier_2_1_score', 'tier_2_2_score', 'tier_2_3_score',
                'tier_3_1_score', 'tier_3_2_score', 'tier_4_1_score']:
        try:
            # Replace NaN with 0 before converting to int
            score = 0 if pd.isna(row[col]) else int(row[col])
            scores.append(score)
        except (ValueError, KeyError):
            scores.append(0)  # Use 0 as default score for any errors
    
    return sum(sorted(scores)[:n])


#### Configure page layout ##### 
st.set_page_config(layout="wide")
#st.markdown("""<meta name="viewport" content="width=device-width, initial-scale=1.0">""", unsafe_allow_html=True)
st.markdown('<h1 style="color: white;">🏆 2026 Masters Leaderboard 🏆</h1>', unsafe_allow_html=True)
st.markdown(
"""
<style>
.stApp {
    background-color: #174038;
}
</style>
""",
unsafe_allow_html=True
)

################################

# Fetching Masters scores (year should match the picks CSV)
scores = get_masters_scores(year=2026)

if scores.empty:
    st.stop()

picks = pd.read_csv('masters_picks.csv')
picks = picks.drop(columns = ['PAYMENT - Select Option Below & Pay Prior to Submission'])
picks = picks.apply(lambda x: x.str.strip() if x.dtype == "object" else x)

# Merging golfers_df with masters_data_df on golfer names
for col in ['tier_1_1', 'tier_1_2', 'tier_1_3', 'tier_2_1', 'tier_2_2', 'tier_2_3', 'tier_3_1', 'tier_3_2', 'tier_4_1']:
    if col == 'tier_1_1':
        merged_df = pd.merge(picks, scores, how='left', left_on=col, right_on='golfer_name')
        merged_df = merged_df.drop(columns = 'golfer_name')
        merged_df = merged_df.rename(columns = {'score': f'{col}_score', 'thru': f'{col}_thru'})
    else:
        merged_df = pd.merge(merged_df, scores, how ='left', left_on=col, right_on = 'golfer_name')
        merged_df = merged_df.drop(columns = ['golfer_name'])
        merged_df = merged_df.rename(columns = {'score': f'{col}_score', 'thru': f'{col}_thru'})
print(merged_df)
# Calculate top n scores
merged_df['top_6_score'] = merged_df.apply(lambda row: calculate_top_n(row, n=6), axis=1)
merged_df['top_7_score'] = merged_df.apply(lambda row: calculate_top_n(row, n=7), axis=1)
merged_df['top_8_score'] = merged_df.apply(lambda row: calculate_top_n(row, n=8), axis=1)

merged_df = merged_df.rename(columns = {'name': 'Name', 'tier_1_1': '1', 'tier_1_2': '2', 'tier_1_3': '3', 'tier_2_1': '4', 'tier_2_2': '5', 'tier_2_3': '6', 'tier_3_1': '7', 'tier_3_2': '8', 'tier_4_1': '9', 
                                        'tier_1_1_score': '1 Score', 'tier_1_2_score': '2 Score', 'tier_1_3_score': '3 Score', 'tier_2_1_score': '4 Score', 'tier_2_2_score': '5 Score', 'tier_2_3_score': '6 Score', 'tier_3_1_score': '7 Score', 'tier_3_2_score': '8 Score', 'tier_4_1_score': '9 Score',
                                        'top_6_score': 'Score', 'top_7_score': 'Tiebreak'})
tier_cols = ['tier_1_1', 'tier_1_2', 'tier_1_3', 'tier_2_1', 'tier_2_2', 'tier_2_3', 'tier_3_1', 'tier_3_2', 'tier_4_1']

# Build pick display strings sorted by score (best first) for each row
def _build_sorted_picks(row):
    picks = []
    for tcol in tier_cols:
        name = row[tcol.replace('tier_', '').replace('_', '', 1)] if False else row.get(tcol, '')
    # Gather name, score, thru for each pick
    picks = []
    for tcol in tier_cols:
        col_num = tier_cols.index(tcol) + 1
        name_col = str(col_num)
        score_col = f'{col_num} Score'
        thru_col = f'{tcol}_thru'
        name = row.get(name_col, '')
        score = row.get(score_col, 0)
        try:
            score_val = float(score) if not pd.isna(score) else 0
        except (ValueError, TypeError):
            score_val = 0
        thru = str(row.get(thru_col, '') or '')
        hole_indicator = f'⛳{thru} ' if thru else ''
        display = f'{hole_indicator}{name} ({score})'
        picks.append((score_val, display))
    picks.sort(key=lambda x: x[0])
    return picks

for idx in merged_df.index:
    sorted_picks = _build_sorted_picks(merged_df.loc[idx])
    for i, (_, display) in enumerate(sorted_picks, 1):
        merged_df.at[idx, f'Pick: {i}'] = display
merged_df['Rank'] = merged_df['Score'].rank(method='min').astype(int)
# Add blank col for spacing
merged_df[''] = ''

# final_df = merged_df[['Rank', 'Score', 'Tiebreak', '', 'Pick: 1', 'Pick: 2', 'Pick: 3', 'Pick: 4', 'Pick: 5', 'Pick: 6', 'Pick: 7', 'Pick: 8', 'Pick: 9']]
# Add a text input for filtering by 'Name'
col1, col2 = st.columns([1, 1])
names_full  = merged_df['Name'].sort_values()
names = [name for name in names_full]
default_option = ""
options = [default_option] + sorted(list(set(names)))

with col1: 
    name_filter = st.selectbox('Filter by Name',  options)

# Filter the dataframe based on the input
filtered_df = merged_df[merged_df['Name'].str.contains(name_filter, case=False)]
score_columns = [col for col in filtered_df.columns if 'Score' in col]
for col in score_columns:
    filtered_df[col] = filtered_df[col].astype(str)

pick_rename = {f'Pick: {i}': f'Score {i}' for i in range(1, 10)}
display_cols = ['Rank', 'Name', 'Score', 'Tiebreak', '', 'Pick: 1', 'Pick: 2', 'Pick: 3', 'Pick: 4', 'Pick: 5', 'Pick: 6', 'Pick: 7', 'Pick: 8', 'Pick: 9']
display_df = filtered_df.sort_values(by='Rank')[display_cols].rename(columns=pick_rename)

# Now display the DataFrame
st.dataframe(data=display_df,
            hide_index=True,
            width=2000,
            height=800)
# def display_messages(messages):
#     st.subheader("Chat Messages")
#     for message in reversed(messages):  # Display newest messages at the top
#         st.write(message)
        
# # Create a sample DataFrame for storing messages
# messages_df = pd.read_csv('messages.csv')
# # Text area for users to input their message
# message_input = st.text_area("Type your message here:")

# if st.button("Send (and see msgs)"):
#     if message_input:
#         # Add the message to the DataFrame
#         messages_df = pd.concat([messages_df, pd.DataFrame({"User": "User", "Message": message_input}, index=[0]*len(message_input))], ignore_index = True)
#         # Display the updated messages
#         display_messages(messages_df["Message"].tolist())
#     else:
#         st.warning("Please enter a message.")
# messages_df.to_csv('messages.csv')


