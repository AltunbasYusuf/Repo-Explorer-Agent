import os


class Calculator:
    def add(self, a, b):
        return a + b

    def subtract(self, a, b):
        return a - b


def multiply(a, b):
    return a * b


def divide(a, b):
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b