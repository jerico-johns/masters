import streamlit as st
import requests
import pandas as pd
import numpy as np

def get_masters_scores():
    url = "https://site.web.api.espn.com/apis/site/v2/sports/golf/leaderboard?league=pga"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
    }
    
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        tournament = data['events'][0]['name']
        leaderboard = data['events'][0]['competitions'][0]['competitors']
        player_data = []
        for player in leaderboard:
            name = player['athlete']['displayName']
            # Fix names 
            if name == 'Byeong-Hun An': 
                name = 'Byeong Hun An'
            elif name == 'Cameron Davis': 
                name = 'Cam Davis'
            elif name == 'Ludvig Aberg': 
                name = 'Ludvig Åberg'
            elif name == 'Nicolai Højgaard': 
                name = 'Nicolai Hojgaard'
            elif name == 'Thorbjorn Olesen': 
                name = 'Thorbjørn Olesen'
            elif name == 'Joaquín Niemann': 
                name = 'Joaquin Niemann'
            
            position = player['status']['period']
            
            score = player['score']['displayValue']
            if score == 'E': 
                score = 0
            else: 
                score = int(score)
                
            player_data.append({'golfer_name': name, 'score': score})
        
        df = pd.DataFrame(player_data)
        df['score'] = df['score'].astype(int)
        return df
    else:
        return 'API Error'

def calculate_top_n(row, n):
    scores = [row['tier_1_1_score'], row['tier_1_2_score'], row['tier_1_3_score'], row['tier_2_1_score'], row['tier_2_2_score'], row['tier_2_3_score'], row['tier_3_2_score'], row['tier_4_1_score']]
    return sum(sorted(scores)[:n])


#### Configure page layout ##### 
st.set_page_config(layout="wide")
#st.markdown("""<meta name="viewport" content="width=device-width, initial-scale=1.0">""", unsafe_allow_html=True)
st.title('🏆 Masters Leaderboard 🏆')
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

# Fetching Masters scores
scores = get_masters_scores()

picks = pd.read_csv('masters_picks.csv')

# Merging golfers_df with masters_data_df on golfer names
for col in ['tier_1_1', 'tier_1_2', 'tier_1_3', 'tier_2_1', 'tier_2_2', 'tier_2_3', 'tier_3_1', 'tier_3_2', 'tier_4_1']: 
    if col == 'tier_1_1': 
        merged_df = pd.merge(picks, scores, how='left', left_on=col, right_on='golfer_name')
        merged_df = merged_df.drop(columns = 'golfer_name')
        merged_df = merged_df.rename(columns = {'score': f'{col}_score'})
    else: 
        merged_df = pd.merge(merged_df, scores, how ='left', left_on=col, right_on = 'golfer_name')
        merged_df = merged_df.drop(columns = ['golfer_name'])
        merged_df = merged_df.rename(columns = {'score': f'{col}_score'})

# Calculate top n scores
merged_df['top_6_score'] = merged_df.apply(lambda row: calculate_top_n(row, n=6), axis=1)
merged_df['top_7_score'] = merged_df.apply(lambda row: calculate_top_n(row, n=7), axis=1)
merged_df['top_8_score'] = merged_df.apply(lambda row: calculate_top_n(row, n=8), axis=1)

merged_df = merged_df.rename(columns = {'name': 'Name', 'tier_1_1': '1', 'tier_1_2': '2', 'tier_1_3': '3', 'tier_2_1': '4', 'tier_2_2': '5', 'tier_2_3': '6', 'tier_3_1': '7', 'tier_3_2': '8', 'tier_4_1': '9', 
                                        'tier_1_1_score': '1 Score', 'tier_1_2_score': '2 Score', 'tier_1_3_score': '3 Score', 'tier_2_1_score': '4 Score', 'tier_2_2_score': '5 Score', 'tier_2_3_score': '6 Score', 'tier_3_1_score': '7 Score', 'tier_3_2_score': '8 Score', 'tier_4_1_score': '9 Score',
                                        'top_6_score': 'Score', 'top_7_score': 'Tiebreak'})
for i in range(1, 10): 
    merged_df[f'Pick: {i}'] = merged_df[str(i)] + ' (' + merged_df[f'{i} Score'].astype(str) + ')'
merged_df['Rank'] = merged_df['Score'].rank(method='min').astype(int)
# Add blank col for spacing
merged_df[''] = ''

# final_df = merged_df[['Rank', 'Score', 'Tiebreak', '', 'Pick: 1', 'Pick: 2', 'Pick: 3', 'Pick: 4', 'Pick: 5', 'Pick: 6', 'Pick: 7', 'Pick: 8', 'Pick: 9']]
# Add a text input for filtering by 'Name'
col  = st.columns(1)
with col: 
    name_filter = st.selectbox('Filter by Name', merged_df['Name'].sort_values().unique())

    # Filter the dataframe based on the input
    filtered_df = merged_df[merged_df['Name'].str.contains(name_filter, case=False)]

    st.dataframe(data = merged_df.sort_values(by = 'Rank'), hide_index=True, column_order = ['Rank', 'Name', 'Score', 'Tiebreak', '', 'Pick: 1', 'Pick: 2', 'Pick: 3', 'Pick: 4', 'Pick: 5', 'Pick: 6', 'Pick: 7', 'Pick: 8', 'Pick: 9'])
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


