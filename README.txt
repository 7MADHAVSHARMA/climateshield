\# ClimateShield — Climate Risk Awareness and Early Response Platform



ClimateShield is a web-based SDG 13 climate-risk awareness prototype.

It retrieves weather data, identifies locations, classifies climate risks,

provides safety guidance, and supports optional email alerts.



\## Features



\- Search any city or address

\- Use browser GPS location

\- Retrieve real-time weather data

\- Classify climate risks as Low, Moderate, High, or Severe

\- Detect heat, rainfall, wind, and potential flood-related risks

\- Display safety guidance

\- Display interactive OpenStreetMap map

\- User registration and login

\- Save locations for climate alerts

\- Enable email alerts

\- Send email alerts using Brevo API



\## Local Setup



Create a virtual environment:



```bash

python -m venv .venv

```



Activate on Windows:



```bash

.venv\\Scripts\\activate

```



Activate on macOS/Linux:



```bash

source .venv/bin/activate

```



Install dependencies:



```bash

pip install -r requirements.txt

```



Create a `.env` file or set environment variables:



```bash

SECRET\_KEY=your-secret-key

BREVO\_API\_KEY=your-brevo-api-key

BREVO\_SENDER\_EMAIL=your-verified-sender-email

NOMINATIM\_USER\_AGENT=ClimateShieldStudentProject/1.0 (your-email@example.com)

```



Run locally:



```bash

flask --app api/index.py run

```



Open:



```text

http://127.0.0.1:5000

```



\## Vercel Deployment



1\. Push this project to GitHub.

2\. Open Vercel.

3\. Import the GitHub repository.

4\. Add environment variables:

&#x20;  - SECRET\_KEY

&#x20;  - BREVO\_API\_KEY

&#x20;  - BREVO\_SENDER\_EMAIL

&#x20;  - NOMINATIM\_USER\_AGENT

5\. Deploy.

6\. Open the generated `.vercel.app` domain.



\## Important Notice



This is an educational prototype. It is not an official emergency warning

or disaster-prediction system. Always follow local government and emergency

service advisories.

