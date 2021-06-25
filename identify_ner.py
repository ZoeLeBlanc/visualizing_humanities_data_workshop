# Importing libraries

import pandas as pd
import nltk
from nltk.corpus import stopwords
import string
import spacy
from progress.bar import IncrementalBar
# Load in spacy model
# python3 -m spacy download en_core_web_lg
nlp = spacy.load('en_core_web_lg')

# Read in full dataset scraped from dh humanist websited, includes data from 1987-2019
humanist_vols = pd.read_csv('web_scraped_humanist_listserv.csv')
# Subset data to only includes rows with dates
humanist_vols_dates = humanist_vols[humanist_vols.dates.str.contains('-')]
# Create new column containing origintal text length
humanist_vols_dates.loc[:,'original_text_length'] = humanist_vols_dates.text.apply(len)

humanist_vols_dates.loc[:,'text_lowercase'] = humanist_vols_dates.text.str.lower()

def tokenize_text_split_monthly(rows):
    tokens = nltk.word_tokenize(rows.text_lowercase)
    val = round(len(tokens) / 12)
    split_tokens = [tokens[i:i + val] for i in range(0, len(tokens), val)]
    if len(split_tokens) > 12:
        combine_rows = split_tokens[11] + split_tokens[12]
        final_tokens = split_tokens[0:11]
        final_tokens.insert(len(final_tokens), combine_rows)
        split_tokens = final_tokens
    rows['split_tokens'] = split_tokens
    return rows

humanist_vols_split = humanist_vols_dates.apply(tokenize_text_split_monthly, axis=1)
humanist_vols_split = humanist_vols_split.explode('split_tokens')
humanist_vols_split = humanist_vols_split[['dates', 'split_tokens']]
humanist_vols_split.loc[:,'month'] = humanist_vols_split.groupby('dates').cumcount() + 1
humanist_vols_split.loc[:,'text_lowercase'] = humanist_vols_split.split_tokens.agg(' '.join)

processing = IncrementalBar('identifying named entities', max=len(humanist_vols_split.index))

def get_ner(row, types):
    processing.next()
    ner_terms= ''
    cleaned_terms = ''

    cleaned_text = ' '.join([token for token in row.split_tokens if ( token not in string.punctuation) and (token not in stopwords.words('english'))])

    spacy_text = nlp(cleaned_text)
    for ent in spacy_text:
        if len(ent.ent_type_) > 0 or ent.is_alpha:
            if( ent.is_punct == False) and (any(i.isdigit() for i in ent.text) == False) and (ent.is_stop ==False):
                text = ('').join(ent.text.split('.')) if '.' in ent.text else ent.text
                cleaned_terms += text + ' '
                if ent.ent_type_ in types:
                    ner_terms += text + ' '
    row['ner_terms'] = ner_terms
    row['cleaned_terms'] = cleaned_terms          
    return row
ner_types = ['LOC', 'GPE']
humanist_vols_split = humanist_vols_split.apply(get_ner, types=ner_types, axis=1, result_type='expand')
processing.finish()

humanist_vols_split.to_csv('humanist_vols_ner_tokens.csv', index=False)