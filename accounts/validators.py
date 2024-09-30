# python
import datetime


def is_valid_south_african_id(id_number):
    # Ensure the ID number is 13 digits long
    if len(id_number) != 13 or not id_number.isdigit():
        return False
    
    # Extract the date of birth from the first 6 digits
    dob = id_number[:6]
    try:
        birth_date = datetime.datetime.strptime(dob, '%y%m%d')
        # Ensure the birth date is realistic (e.g., between 1900 and the current year)
        if not (datetime.datetime(1900, 1, 1) <= birth_date <= datetime.datetime.now()):
            return False
    except ValueError:
        return False  # Invalid date
    
    # Check if citizenship digit is valid (11th digit: 0 for citizen, 1 for resident)
    citizenship_digit = id_number[10]
    if citizenship_digit not in ['0', '1']:
        return False
    
    # Perform the Luhn check on the ID number
    if not luhn_checksum_is_valid(id_number):
        return False
    
    return True

def luhn_checksum_is_valid(id_number):
    def digits_of(n):
        return [int(d) for d in str(n)]
    
    digits = digits_of(id_number)
    odd_digits = digits[-1::-2]
    even_digits = digits[-2::-2]
    
    checksum = sum(odd_digits)
    for d in even_digits:
        checksum += sum(digits_of(d * 2))
    
    return checksum % 10 == 0

