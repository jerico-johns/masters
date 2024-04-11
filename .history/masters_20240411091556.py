import streamlit as st
import requests
import pandas as pd
import numpy as np
from bs4 import BeautifulSoup

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
        
        # Convert the data list into a pandas DataFrame
        df = pd.DataFrame(data)
        df = df[[2, 3]]
        df.columns = ['golfer_name', 'score']
        
        df["golfer_name"] = df["golfer_name"].replace({
            'Nicolai Højgaard': 'Nicolai Hojgaard',
            'Thorbjorn Olesen': 'Thorbjørn Olesen',
            'Joaquín Niemann': 'Joaquin Niemann', 
            'Christo Lamprecht (a)': 'Christo Lamprecht', 
            'Jasper Stubbs (a)': 'Jasper Stubbs',
            'Neal Shipley (a)': 'Neil Shipley', 
            'Santiago de la Fuente (a)': 'Santiago de la Fuente (a)'
        })
        
        df["score"] = df["score"].replace({
            'E': 0
        })
        df["score"] = df["score"].apply(lambda x: int(x))
        
        return df 
        
    else:
        return f"Failed to retrieve ESPN scores. Status code:{response.status_code}"

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
col1, col2 = st.columns([1, 1])
names = merged_df['Name'].sort_values().unique()
default_option = ""
options = [default_option] + list(names)

with col1: 
    name_filter = st.selectbox('Filter by Name',  options)

# Filter the dataframe based on the input
filtered_df = merged_df[merged_df['Name'].str.contains(name_filter, case=False)]

st.dataframe(data = filtered_df.sort_values(by = 'Rank'), hide_index=True, column_order = ['Rank', 'Name', 'Score', 'Tiebreak', '', 'Pick: 1', 'Pick: 2', 'Pick: 3', 'Pick: 4', 'Pick: 5', 'Pick: 6', 'Pick: 7', 'Pick: 8', 'Pick: 9'])
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


