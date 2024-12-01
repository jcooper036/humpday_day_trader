from google.cloud import secretmanager
import google_crc32c


def get_gsm_secret(secret_name: str):
    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/humpday-day-trader/secrets/{secret_name}/versions/latest"
    response = client.access_secret_version(request={"name": name})
    crc32c = google_crc32c.Checksum()
    crc32c.update(response.payload.data)
    if response.payload.data_crc32c != int(crc32c.hexdigest(), 16):
        print("Data corruption detected.")
        return response
    payload = response.payload.data.decode("UTF-8")
    return payload
