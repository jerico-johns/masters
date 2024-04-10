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
            
            position = player['status']['period']
            score = player['score']['value']
            player_data.append({'golfer_name': name, 'score': score})
        
        df = pd.DataFrame(player_data)
        return df
    else:
        return 'API Error'

def calculate_top_n(row, n):
    scores = [row['tier_1_1_score'], row['tier_1_2_score'], row['tier_1_3_score'], row['tier_2_1_score'], row['tier_2_2_score'], row['tier_2_3_score'], row['tier_3_2_score'], row['tier_4_1_score']]
    return sum(sorted(scores)[:n])

def main():
    #### Configure page layout ##### 
    st.title('Masters Leaderboard')
    ################################
    
    # Fetching Masters scores
    scores = get_masters_scores()

    # Insert dummy data (TODO: Delete)
    for idx, row in scores.iterrows(): 
        scores.loc[idx, 'score'] = np.random.randint(0, 72)

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

    merged_df = merged_df.rename(columns = {'name': 'Name', 'tier_1_1': '1.1', 'tier_1_2': '1.2', 'tier_1_3': '1.3', 'tier_2_1': '2.1', 'tier_2_2': '2.2', 'tier_2_3': '2.3', 'tier_3_1': '3.1', 'tier_3_2': '3.2', 'tier_4_1': '4.1', 
                                            'tier_1_1_score': '1.1 Score', 'tier_1_2_score': '1.2 Score', 'tier_1_3_score': '1.3 Score', 'tier_2_1_score': '2.1 Score', 'tier_2_2_score': '2.2 Score', 'tier_2_3_score': '2.3 Score', 'tier_3_1_score': '3.1 Score', 'tier_3_2_score': '3.2 Score', 'tier_4_1_score': '4.1 Score',
                                            'top_6_score': 'Score', 'top_7_score': '(Tiebreaker)'})
    st.dataframe(data = merged_df, hide_index=True, column_order = ['Name', 'Score', 'Tiebreaker'])

if __name__ == "__main__":
    main()
