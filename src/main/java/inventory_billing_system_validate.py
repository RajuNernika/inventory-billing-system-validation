#!/bin/python3
import random
import string
import requests
import json
from datetime import datetime, timedelta
from result_output import ResultOutput
import os
import sys
import psycopg2
from psycopg2 import Error


class PostgreSQL:
    def __init__(self, db_url, db_name, db_username, db_password):
        self.db_url = db_url
        self.db_name = db_name
        self.db_username = db_username
        self.db_password = db_password
        self.connection = None
        self.cursor = None

    def connect_to_db(self):
        try:
            self.connection = psycopg2.connect(
                host=self.db_url,
                database=self.db_name,
                user=self.db_username,
                password=self.db_password
            )
            if self.connection:
                self.cursor = self.connection.cursor()
        except (Exception, Error) as error:
            pass

    def disconnect_from_db(self):
        if self.cursor:
            self.cursor.close()
        if self.connection:
            self.connection.close()

    def truncate_table(self, table_name):
        if not self.cursor:
            return
        try:
            query = f"TRUNCATE TABLE {table_name} CASCADE"
            self.cursor.execute(query)
            self.connection.commit()
        except (Exception, Error) as error:
            pass

    def get_all_records(self, table_name):
        if not self.cursor:
            return None
        try:
            query = f"SELECT * FROM {table_name};"
            self.cursor.execute(query)
            records = self.cursor.fetchall()
            return records
        except (Exception, Error) as error:
            return None

    def getItemById(self, table_name, id):
        if not self.cursor:
            return None
        try:
            query = f"SELECT * FROM {table_name} WHERE id={id};"
            self.cursor.execute(query)
            records = self.cursor.fetchall()
            return records
        except (Exception, Error) as error:
            return None

    def create_document_product(self, name, price, quantity):
        if not self.cursor:
            return None
        try:
            query = f"INSERT INTO products (name, price, quantity) VALUES (%s, %s, %s) RETURNING id;"
            self.cursor.execute(query, (name, price, quantity))
            self.connection.commit()
            product_id = self.cursor.fetchone()[0]
            return product_id
        except (Exception, Error) as error:
            return None

    def create_document_customer(self, name, email):
        if not self.cursor:
            return None
        try:
            query = f"INSERT INTO customers (name, email) VALUES (%s, %s) RETURNING id;"
            self.cursor.execute(query, (name, email))
            self.connection.commit()
            customer_id = self.cursor.fetchone()[0]
            return customer_id
        except (Exception, Error) as error:
            return None

    def clear_tables(self):
        tables = ["products", "customers", "billing"]
        for table in tables:
            self.truncate_table(table)


def generate_random_string(length):
    letters = string.ascii_letters + string.digits
    return "".join(random.choice(letters) for _ in range(length))


class Activity(PostgreSQL):
    def __init__(self):
        self.product_id = None
        self.customer_id = None
        self.billing_id = None
        self.isCreatedSuccessful = False
        self.isBillingCreatedSuccessful = False
        self.billing_quantity = 0
        super().__init__("localhost", "database_name", "postgres", "password")

    def testcase_check_for_successful_product_creation(self, test_object):
        testcase_description = "Check for successful product creation"
        expected_result = "product created successfully!"
        actual = "product creation was not successful!"
        marks = 10
        marks_obtained = 0

        test_object.update_pre_result(testcase_description, expected_result)

        try:
            api_url = "http://localhost:8080/api/products"
            headers = {"Content-Type": "application/json"}
            payload = {
                "name": generate_random_string(10),
                "price": random.randint(100, 1000),
                "quantity": random.randint(1, 100),
            }

            try:
                response = requests.post(api_url, json=payload, headers=headers, timeout=5)
                response.raise_for_status()
            except requests.RequestException as e:
                test_object.update_result(
                    0, expected_result, "API call failed", testcase_description, "N/A", marks, marks_obtained
                )
                return

            json_data = response.json()
            product_id = json_data.get('id', None)

            if product_id is not None:
                self.product_id = product_id
                self.connect_to_db()
                products = self.getItemById("products", product_id)
                self.disconnect_from_db()

                if products is not None and len(products) > 0 and products[0][1] == payload['name']:
                    marks_obtained = marks
                    self.isCreatedSuccessful = True
                    return test_object.update_result(
                        1, expected_result, expected_result, testcase_description, "N/A", marks, marks_obtained
                    )
            return test_object.update_result(
                0, expected_result, actual, testcase_description, "N/A", marks, marks_obtained
            )
        except Exception as e:
            test_object.update_result(
                0, expected_result, actual, testcase_description, "N/A", marks, marks_obtained
            )
            test_object.eval_message["testcase_name"] = str(e)

    def testcase_check_for_successful_product_retrieval_by_id(self, test_object):
        testcase_description = "Check for successful product retrieval by id"
        expected_result = "product retrieved successfully!"
        actual = "product not retrieved!"
        marks = 10
        marks_obtained = 0

        test_object.update_pre_result(testcase_description, expected_result)

        try:
            self.connect_to_db()
            product = {
                "name": generate_random_string(10),
                "price": random.randint(100, 1000),
                "quantity": random.randint(1, 100),
            }
            product_id = self.create_document_product(product["name"], product["price"], product["quantity"])
            self.disconnect_from_db()

            if product_id is None:
                test_object.update_result(
                    0, expected_result, "product creation failed! Failed to connect to db",
                    testcase_description, "N/A", marks, marks_obtained
                )
                return

            api_url = f"http://localhost:8080/api/products/{product_id}"
            headers = {"Content-Type": "application/json"}

            response = requests.get(api_url, headers=headers, timeout=5)
            json_data = response.json()

            if response.status_code == 200 and json_data['id'] == product_id:
                marks_obtained = marks
                return test_object.update_result(
                    1, expected_result, expected_result, testcase_description, "N/A", marks, marks_obtained
                )
            return test_object.update_result(
                0, expected_result, actual, testcase_description, "N/A", marks, marks_obtained
            )
        except Exception as e:
            test_object.update_result(
                0, expected_result, actual, testcase_description, "N/A", marks, marks_obtained
            )
            test_object.eval_message["testcase_name"] = str(e)

    def testcase_check_for_update_product(self, test_object):
        testcase_description = "Check for updating a product"
        expected_result = "product updated successfully!"
        actual = "product not updated!"
        marks = 10
        marks_obtained = 0

        test_object.update_pre_result(testcase_description, expected_result)

        try:
            self.connect_to_db()
            product = {
                "name": generate_random_string(10),
                "price": random.randint(100, 1000),
                "quantity": random.randint(1, 100),
            }
            product_id = self.create_document_product(product["name"], product["price"], product["quantity"])
            self.disconnect_from_db()

            if product_id is None:
                test_object.update_result(
                    0, expected_result, "product creation failed!", testcase_description, "N/A", marks, marks_obtained
                )
                return

            api_url = f"http://localhost:8080/api/products/{product_id}"
            headers = {"Content-Type": "application/json"}
            payload = {
                "name": generate_random_string(10),
                "price": random.randint(100, 1000),
                "quantity": random.randint(1, 100),
            }

            response = requests.put(api_url, json=payload, headers=headers, timeout=5)

            if response.status_code == 200:
                self.connect_to_db()
                products = self.getItemById("products", product_id)
                self.disconnect_from_db()

                if products and len(products) > 0 and products[0][1] == payload['name']:
                    marks_obtained = marks
                    return test_object.update_result(
                        1, expected_result, expected_result, testcase_description, "N/A", marks, marks_obtained
                    )
            return test_object.update_result(
                0, expected_result, actual, testcase_description, "N/A", marks, marks_obtained
            )
        except Exception as e:
            test_object.update_result(
                0, expected_result, actual, testcase_description, "N/A", marks, marks_obtained
            )
            test_object.eval_message["testcase_name"] = str(e)

    def testcase_check_for_delete_product(self, test_object):
        testcase_description = "Check for deleting a product"
        expected_result = "product deleted successfully!"
        actual = "product not deleted!"
        marks = 10
        marks_obtained = 0

        test_object.update_pre_result(testcase_description, expected_result)

        try:
            self.connect_to_db()
            product = {
                "name": generate_random_string(10),
                "price": random.randint(100, 1000),
                "quantity": random.randint(1, 100),
            }
            product_id = self.create_document_product(product["name"], product["price"], product["quantity"])
            self.disconnect_from_db()

            if product_id is None:
                test_object.update_result(
                    0, expected_result, "product creation failed!", testcase_description, "N/A", marks, marks_obtained
                )
                return

            api_url = f"http://localhost:8080/api/products/{product_id}"
            headers = {"Content-Type": "application/json"}

            response = requests.delete(api_url, headers=headers, timeout=5)

            if response.status_code == 200:
                self.connect_to_db()
                products = self.getItemById("products", product_id)
                self.disconnect_from_db()

                if products is None or len(products) == 0:
                    marks_obtained = marks
                    return test_object.update_result(
                        1, expected_result, expected_result, testcase_description, "N/A", marks, marks_obtained
                    )
            return test_object.update_result(
                0, expected_result, actual, testcase_description, "N/A", marks, marks_obtained
            )
        except Exception as e:
            test_object.update_result(
                0, expected_result, actual, testcase_description, "N/A", marks, marks_obtained
            )
            test_object.eval_message["testcase_name"] = str(e)

    def testcase_check_for_successful_customer_creation(self, test_object):
        testcase_description = "Check for successful customer creation"
        expected_result = "customer created successfully!"
        actual = "customer creation was not successful!"
        marks = 10
        marks_obtained = 0

        test_object.update_pre_result(testcase_description, expected_result)

        try:
            api_url = "http://localhost:8080/api/customers"
            headers = {"Content-Type": "application/json"}
            payload = {
                "name": generate_random_string(10),
                "email": generate_random_string(10) + "@gmail.com",
            }

            try:
                response = requests.post(api_url, json=payload, headers=headers, timeout=5)
                response.raise_for_status()
            except requests.RequestException as e:
                test_object.update_result(
                    0, expected_result, "API call failed", testcase_description, "N/A", marks, marks_obtained
                )
                return

            json_data = response.json()
            customer_id = json_data.get('id', None)

            if customer_id is not None:
                self.customer_id = customer_id
                self.connect_to_db()
                customers = self.getItemById("customers", customer_id)
                self.disconnect_from_db()

                if customers is not None and len(customers) > 0 and customers[0][1] == payload['name']:
                    marks_obtained = marks
                    return test_object.update_result(
                        1, expected_result, expected_result, testcase_description, "N/A", marks, marks_obtained
                    )
            return test_object.update_result(
                0, expected_result, actual, testcase_description, "N/A", marks, marks_obtained
            )
        except Exception as e:
            test_object.update_result(
                0, expected_result, actual, testcase_description, "N/A", marks, marks_obtained
            )
            test_object.eval_message["testcase_name"] = str(e)

    def testcase_check_get_all_customers(self, test_object):
        testcase_description = "Check for retrieving all customers"
        expected_result = "All customers retrieved successfully!"
        actual = "All customers not retrieved!"
        marks = 10
        marks_obtained = 0

        test_object.update_pre_result(testcase_description, expected_result)

        try:
            self.connect_to_db()
            customer = {
                "name": generate_random_string(10),
                "email": generate_random_string(10) + "@gmail.com",
            }
            customer_id = self.create_document_customer(customer["name"], customer["email"])
            self.disconnect_from_db()

            if customer_id is None:
                test_object.update_result(
                    0, expected_result, "customer creation failed!", testcase_description, "N/A", marks, marks_obtained
                )
                return

            api_url = "http://localhost:8080/api/customers"
            headers = {"Content-Type": "application/json"}

            response = requests.get(api_url, headers=headers, timeout=5)
            json_data = response.json()
            customer_ids = [c['id'] for c in json_data]

            if response.status_code == 200 and len(json_data) > 0 and customer_id in customer_ids:
                marks_obtained = marks
                return test_object.update_result(
                    1, expected_result, expected_result, testcase_description, "N/A", marks, marks_obtained
                )
            return test_object.update_result(
                0, expected_result, actual, testcase_description, "N/A", marks, marks_obtained
            )
        except Exception as e:
            test_object.update_result(
                0, expected_result, actual, testcase_description, "N/A", marks, marks_obtained
            )
            test_object.eval_message["testcase_name"] = str(e)

    def testcase_check_for_create_billing(self, test_object):
        testcase_description = "Check for successful billing creation"
        expected_result = "billing created successfully!"
        actual = "billing creation was not successful!"
        marks = 10
        marks_obtained = 0

        test_object.update_pre_result(testcase_description, expected_result)

        if not self.isCreatedSuccessful:
            test_object.update_result(
                0, expected_result, "product creation failed! dependent on product creation",
                testcase_description, "N/A", marks, marks_obtained
            )
            return
        if self.customer_id is None:
            test_object.update_result(
                0, expected_result, "customer creation failed! dependent on customer creation",
                testcase_description, "N/A", marks, marks_obtained
            )
            return

        try:
            api_url = "http://localhost:8081/api/billing"
            headers = {"Content-Type": "application/json"}
            payload = {
                "cust_id": self.customer_id,
                "prod_id": self.product_id,
                "quantity": random.randint(1, 10)
            }

            try:
                response = requests.post(api_url, json=payload, headers=headers, timeout=5)
                response.raise_for_status()
            except requests.RequestException as e:
                test_object.update_result(
                    0, expected_result, "API call failed", testcase_description, "N/A", marks, marks_obtained
                )
                return

            json_data = response.json()
            billing_id = json_data.get('id', None)

            if billing_id is not None:
                self.billing_id = billing_id
                self.connect_to_db()
                billings = self.getItemById("billing", billing_id)
                self.disconnect_from_db()

                if billings and len(billings) > 0 and billings[0][1] == payload['cust_id']:
                    marks_obtained = marks
                    self.isBillingCreatedSuccessful = True
                    return test_object.update_result(
                        1, expected_result, expected_result, testcase_description, "N/A", marks, marks_obtained
                    )
            return test_object.update_result(
                0, expected_result, actual, testcase_description, "N/A", marks, marks_obtained
            )
        except Exception as e:
            test_object.update_result(
                0, expected_result, actual, testcase_description, "N/A", marks, marks_obtained
            )
            test_object.eval_message["testcase_name"] = str(e)

    def testcase_check_for_quantity_update_if_product_exists(self, test_object):
        testcase_description = "Check for updating quantity if product is already bought"
        expected_result = "quantity updated successfully!"
        actual = "quantity not updated!"
        marks = 10
        marks_obtained = 0

        test_object.update_pre_result(testcase_description, expected_result)

        if not self.isBillingCreatedSuccessful:
            test_object.update_result(
                0, expected_result, "billing creation failed! dependent on billing creation",
                testcase_description, "N/A", marks, marks_obtained
            )
            return

        try:
            api_url = "http://localhost:8081/api/billing"
            headers = {"Content-Type": "application/json"}
            payload = {
                "cust_id": self.customer_id,
                "prod_id": self.product_id,
                "quantity": random.randint(1, 10)
            }
            self.billing_quantity += payload['quantity']

            response = requests.post(api_url, json=payload, headers=headers, timeout=5)

            if response.status_code in [200, 201]:
                self.connect_to_db()
                billings = self.getItemById("billing", self.billing_id)
                self.disconnect_from_db()

                if billings and len(billings) > 0 and billings[0][3] == self.billing_quantity:
                    marks_obtained = marks
                    return test_object.update_result(
                        1, expected_result, expected_result, testcase_description, "N/A", marks, marks_obtained
                    )
            return test_object.update_result(
                0, expected_result, actual, testcase_description, "N/A", marks, marks_obtained
            )
        except Exception as e:
            test_object.update_result(
                0, expected_result, actual, testcase_description, "N/A", marks, marks_obtained
            )
            test_object.eval_message["testcase_name"] = str(e)

    def testcase_check_for_retrieving_all_billings_by_customer_id(self, test_object):
        testcase_description = "Check for retrieving all billings by customer id"
        expected_result = "All billings retrieved successfully!"
        actual = "All billings not retrieved!"
        marks = 20
        marks_obtained = 0

        test_object.update_pre_result(testcase_description, expected_result)

        if not self.isBillingCreatedSuccessful:
            test_object.update_result(
                0, expected_result, "billing creation failed! dependent on billing creation",
                testcase_description, "N/A", marks, marks_obtained
            )
            return

        try:
            api_url = f"http://localhost:8081/api/billing/{self.customer_id}"
            headers = {"Content-Type": "application/json"}

            response = requests.get(api_url, headers=headers, timeout=5)
            json_data = response.json()
            billing_ids = [b['id'] for b in json_data]

            if response.status_code == 200 and len(json_data) > 0 and self.billing_id in billing_ids:
                marks_obtained = marks
                return test_object.update_result(
                    1, expected_result, expected_result, testcase_description, "N/A", marks, marks_obtained
                )
            return test_object.update_result(
                0, expected_result, actual, testcase_description, "N/A", marks, marks_obtained
            )
        except Exception as e:
            test_object.update_result(
                0, expected_result, actual, testcase_description, "N/A", marks, marks_obtained
            )
            test_object.eval_message["testcase_name"] = str(e)


def start_tests(args):
    args = args.replace("{", "")
    args = args.replace("}", "")
    args = args.split(":")
    args = {"token": args[1]}
    args = json.dumps(args)

    test_object = ResultOutput(args, Activity)
    challenge_test = Activity()
    challenge_test.connect_to_db()
    challenge_test.clear_tables()
    challenge_test.disconnect_from_db()

    challenge_test.testcase_check_for_successful_product_creation(test_object)
    challenge_test.testcase_check_for_successful_product_retrieval_by_id(test_object)
    challenge_test.testcase_check_for_update_product(test_object)
    challenge_test.testcase_check_for_delete_product(test_object)
    challenge_test.testcase_check_for_successful_customer_creation(test_object)
    challenge_test.testcase_check_get_all_customers(test_object)
    challenge_test.testcase_check_for_create_billing(test_object)
    challenge_test.testcase_check_for_quantity_update_if_product_exists(test_object)
    challenge_test.testcase_check_for_retrieving_all_billings_by_customer_id(test_object)

    challenge_test.connect_to_db()
    challenge_test.clear_tables()
    challenge_test.disconnect_from_db()

    result = test_object.result_final()
    result = json.dumps(json.loads(result), indent=4)
    print(result)
    return result


def main():
    args = sys.argv[2]
    start_tests(args)


if __name__ == "__main__":
    main()