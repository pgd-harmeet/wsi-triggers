import azure.functions as func
import logging
import os
import pandas as pd
import requests

from azure.storage.blob import BlobClient
from io import BytesIO

def main(timer: func.TimerRequest) -> None:
    master: requests.Response = requests.get(os.environ['PO_MASTER_URL'])
    daily: requests.Response = requests.get(os.environ['PO_DAILY_URL'])

    master.raise_for_status()
    daily.raise_for_status()

    master: pd.DataFrame = pd.read_csv(BytesIO(master.content))
    daily: pd.DataFrame = pd.read_csv(BytesIO(daily.content))

    if daily.size == 0:
        logging.warning('There are no POs in the daily file')
    else:
        for row in daily.itertuples():
            temp: pd.DataFrame = master[master['PO Header'] == row[1]]
            created_date = temp['Date Expected'].tolist()

            if len(created_date) > 0:
                created_date = created_date[0]
                expected_date = temp['Date Expected'].iloc[0]
                temp = temp.iloc[:, :27]

                header: pd.DataFrame = pd.DataFrame([['ROH', 'I', 'P', row[1], created_date,
                    None, None, expected_date, None, None, 'PGD', 'HN', None,
                    None, None, None, None, None, None, None, None, None]])
                logging.info(f'Generating {len(temp)} SKU(s) for PO {row[1]}')

                po_csv = header.to_csv(header=False, index=False)
                po_csv += temp.to_csv(header=False, index=False)
                export_po(po_csv, f'RO_{row[1]}.csv')
            else:
                logging.warn(f'No SKUs found for PO {row[1]}')

def export_po(po: str, po_name: str) -> None:
    blob = BlobClient.from_connection_string(os.environ['AzureWebJobsStorage'],
        container_name='wsi-pos',
        blob_name=po_name,)

    blob.upload_blob(po, overwrite=True)
