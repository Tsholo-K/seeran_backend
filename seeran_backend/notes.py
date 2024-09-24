"""

    Django test framework

    The Django test framework is a robust testing suite built into Django, designed to help developers ensure that their applications behave as expected.
    It integrates tightly with Python's built-in unittest framework, while adding a host of Django-specific features to make testing easier,
    such as testing views, models, forms, URLs, and custom logic.

    1. Types of Tests in Django

        Django supports various types of tests to cover different aspects of your application:

        Unit Tests:

            These focus on testing small pieces of code, like individual functions or methods, ensuring they return the expected output for a given input.
        
        Integration Tests:

            These test how different parts of your application work together, typically at a higher level(e.g.,
            testing multiple views or how data flows through forms and models).
        
        System/End-to-End Tests:

            These test the application as a whole, usually simulating user behavior (e.g., sending requests to views and checking the rendered HTML).

    2. Setting up Django Tests

        Django comes with a TestCase class (which extends Python's unittest.TestCase), and you can define tests in tests.py files within each app or create a tests/ directory for better organization.

        Steps to write tests:
        
            Import the TestCase Class: Start by importing TestCase in your tests.py file.
            from django.test import TestCase
            Create a Test Case Class: Each test case should be defined as a class, inheriting from TestCase.

            class MyModelTests(TestCase):
                def test_something(self):
                    # Your test logic here

            Writing Test Methods:

                Inside the test class, define methods whose names start with test_. These methods are automatically picked up by the test runner.

                def test_basic_addition(self):
                    self.assertEqual(1 + 1, 2)

            Running Tests

                To run all tests in your project, you can use:

                    python manage.py test

                This command automatically discovers tests in all apps (looking for files named tests.py or tests/ directories),
                creates a temporary test database, runs the tests, and reports the results.

    3. Testing Models

        Testing models typically involves checking that model methods return the correct values and that constraints (e.g., validations) work correctly.

        Example:

            from myapp.models import MyModel

            class MyModelTestCase(TestCase):
                def setUp(self):
                    # Creating initial data
                    MyModel.objects.create(field1="value1", field2="value2")

                def test_model_field_value(self):
                    obj = MyModel.objects.get(field1="value1")
                    self.assertEqual(obj.field2, "value2")

        setUp and tearDown

            setUp:

                Runs before every test method in the class to set up any necessary state (e.g., creating objects or initializing conditions).

            tearDown:

                Cleans up after each test method if needed (not always necessary since Django handles database rollbacks automatically).

    Summary
    
        The Django testing framework offers comprehensive and user-friendly tools to ensure that your Django application behaves as expected.
        You can test models, views, forms, URLs, and templates with ease, leveraging built-in classes like TestCase, Client, and others.
        Using a combination of unit tests, integration tests, and even live server tests, you can build a solid test suite that gives you confidence
        in the stability and reliability of your application.
"""

