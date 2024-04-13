import streamlit as st
import requests
import pandas as pd
import numpy as np
from bs4 import BeautifulSoup
from datetime import datetime
import pytz 


def get_masters_scores(): 
    url = 'https://www.espn.com/golf/leaderboard'
    headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
        }
    response = requests.get(url, headers=headers)
    # Check if the request was successful (status code 200)
    if response.status_code == 200:
        # Parse the HTML content of the webpage
        soup = BeautifulSoup(response.content, "html.parser")
        
        # Find the table with the specified class
        table = soup.find("tbody", class_="Table__TBODY")
        
        # Check if the table was found
        
        # Extract the rows of the table
        rows = table.find_all("tr")
        
        # Initialize an empty list to store the table data
        data = []
        
        # Loop through each row and extract the data
        for row in rows:
            # Extract the cells (td) of the row
            cells = row.find_all("td")
            
            # Extract the text content of each cell and append to the data list
            row_data = [cell.get_text() for cell in cells]
            data.append(row_data)
        headers = soup.find_all('th')
        header_texts = [header.text.strip() for header in headers]
        # Convert the data list into a pandas DataFrame
        df = pd.DataFrame(data)
        df = df[[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]]
        df.columns = [x for x in header_texts]
        
        df['R3'] = df['R3'].replace('--', 0)
        df['R4'] = df['R4'].replace('--', 0)

        # Filter DataFrame
        df = df.dropna(subset = ['PLAYER'])
        filtered_df = df[~df['PLAYER'].str.endswith('(a)')]
        filtered_df = filtered_df[filtered_df['SCORE'] != 'CUT']
        filtered_df["TODAY"] = filtered_df["TODAY"].replace({
                'E': '0', 
            })

        for idx, row in filtered_df.iterrows(): 
                filtered_df.at[idx, 'TODAY'] = int(str(row['TODAY']).strip('+'))
                
        max_today = filtered_df['TODAY'].max() 

        # If we are on Saturday (R3) only add R1 and R2 else add R1 R2 and R3 
        current_date = datetime.now().date().strftime('%d-%m-%Y')

        for idx, row in df.iterrows(): 
            if row['SCORE'] == 'CUT': 
                if current_date == '12-04-2024': 
                    df.at[idx, 'SCORE'] = (int(row['R1']) - 72) + (int(row['R2']) - 72) 
                elif current_date == '13-04-2024': 
                    df.at[idx, 'SCORE'] = (int(row['R1']) - 72) + (int(row['R2']) - 72) + max_today
                elif current_date == '14-04-2024': 
                    df.at[idx, 'SCORE'] = (int(row['R1']) - 72) + (int(row['R2']) - 72) + (int(row['R3']) - 72) + max_today
        
        
        df = df[['PLAYER', 'SCORE']].rename(columns = {'PLAYER': 'golfer_name', 'SCORE': 'score'})
        
        df["golfer_name"] = df["golfer_name"].replace({
                'Ludvig Åberg': 'Ludvig Aberg',
                'Byeong Hun An': 'Byeong-Hun An', 
                'Nicolai Højgaard': 'Nicolai Hojgaard',
                'Joaquín Niemann': 'Joaquin Niemann', 
                'Christo Lamprecht (a)': 'Christo Lamprecht', 
                'Jasper Stubbs (a)': 'Jasper Stubbs',
                'Neal Shipley (a)': 'Neal Shipley', 
                'Santiago de la Fuente (a)': 'Santiago De la Fuente', 
                'Stewart Hagestad (a)': 'Stewart Hagestad', 
                'Thorbjørn Olesen': 'Thorbjorn Olesen'
            })
            
        df["score"] = df["score"].replace({
            'E': '0', 
        })
        df.columns = df.columns.get_level_values(0)
        df = df.dropna()
        for idx, row in df.iterrows(): 
            df.at[idx, 'score'] = int(str(row['score']).strip('+'))
            return df 
    else:
        return f"Failed to retrieve ESPN scores. Status code:{response.status_code}"

def calculate_top_n(row, n):
    scores = [int(row['tier_1_1_score']), int(row['tier_1_2_score']), int(row['tier_1_3_score']), 
              int(row['tier_2_1_score']), int(row['tier_2_2_score']), int(row['tier_2_3_score']), 
              int(row['tier_3_1_score']), int(row['tier_3_2_score']), int(row['tier_4_1_score'])]
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
col1, col2 = st.columns([1, 1])
names_full  = merged_df['Name'].sort_values()
names = [name[:-2] for name in names_full]
default_option = ""
options = [default_option] + sorted(list(set(names)))

with col1: 
    name_filter = st.selectbox('Filter by Name',  options)

# Filter the dataframe based on the input
filtered_df = merged_df[merged_df['Name'].str.contains(name_filter, case=False)]

st.dataframe(data = filtered_df.sort_values(by = 'Rank'), hide_index=True, column_order = ['Rank', 'Name', 'Score', 'Tiebreak', '', 'Pick: 1', 'Pick: 2', 'Pick: 3', 'Pick: 4', 'Pick: 5', 'Pick: 6', 'Pick: 7', 'Pick: 8', 'Pick: 9'], width = 2000)
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


