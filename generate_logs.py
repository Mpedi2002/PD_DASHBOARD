import random
import csv
from datetime import datetime, timedelta
from faker import Faker
import uuid

fake = Faker()

def generate_combined_data(output_file="combined_data.csv", num_entries=100000):
    # Define date range for timestamps (2023 to 2025)
    start_date = datetime(2023, 1, 1)
    end_date = datetime(2025, 12, 31)

    # Define salespersons (fixed team of 10 for consistency across years)
    salespersons = [
        {"id": str(uuid.uuid4()), "name": fake.name()} for _ in range(10)
    ]

    # Open CSV and write header
    with open(output_file, "w", newline='', encoding='utf-8') as file:
        fieldnames = [
            "timestamp", "event_type", "country", "product",
            "price", "unit_cost", "quantity", "channel", "job_type",
            "url", "status", "user_agent", "customer_id",
            "salesperson_id", "salesperson_name"
        ]
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()

        for _ in range(num_entries):
            # Generate a random timestamp in the given range
            ts = fake.date_time_between_dates(
                datetime_start=start_date,
                datetime_end=end_date
            ).replace(microsecond=0)
            country = fake.country_code()
            customer_id = str(uuid.uuid4())  # Unique customer ID

            if random.random() < 0.6:
                # Sale event (60% of records)
                product = random.choice([
                    "AI Assistant", "Smart Prototype", "Analytics Suite"
                ])
                price = random.choice([299, 499, 799, 999])
                unit_cost = round(price * random.uniform(0.5, 0.8), 2)
                quantity = random.randint(1, 20)
                salesperson = random.choice(salespersons)

                record = {
                    "timestamp": ts.isoformat(sep=' '),
                    "event_type": "sale",
                    "country": country,
                    "product": product,
                    "price": price,
                    "unit_cost": unit_cost,
                    "quantity": quantity,
                    "channel": random.choice(["online", "retail", "partner"]),
                    "job_type": random.choice([
                        "Virtual Assistant Subscription",
                        "Prototyping Solution",
                        "Analytics Deployment"
                    ]),
                    "url": "",
                    "status": "",
                    "user_agent": "",
                    "customer_id": customer_id,
                    "salesperson_id": salesperson["id"],
                    "salesperson_name": salesperson["name"]
                }
            else:
                # Web navigation event (40% of records)
                url = random.choice([
                    "/request-demo", "/promotional-event",
                    "/ai-assistant", "/home", "/about"
                ])
                job_type = {
                    "/request-demo": "Demo Request",
                    "/promotional-event": "Promotional Event",
                    "/ai-assistant": "AI Assistant Inquiry",
                    "/home": "Home Page",
                    "/about": "About Page"
                }.get(url, "")

                record = {
                    "timestamp": ts.isoformat(sep=' '),
                    "event_type": "web",
                    "country": country,
                    "product": "",
                    "price": "",
                    "unit_cost": "",
                    "quantity": "",
                    "channel": "",
                    "job_type": job_type,
                    "url": url,
                    "status": random.choice([200, 301, 302, 404, 500]),
                    "user_agent": fake.user_agent(),
                    "customer_id": customer_id,
                    "salesperson_id": "",
                    "salesperson_name": ""
                }

            writer.writerow(record)

    print(f"Generated {num_entries} records in '{output_file}'")

if __name__ == "__main__":
    generate_combined_data()