import struct
import sys

if len(sys.argv) != 3:
    print(f"Usage: {sys.argv[0]} <input_file> <output_file>")
    sys.exit(1)

input_filename = sys.argv[1]
output_filename = sys.argv[2]

with open(input_filename, 'rb') as pointer_to_file:
    parsable_file_in_ram = pointer_to_file.read() 

number_of_audio_samples = len(parsable_file_in_ram) // 8
unpacked_audio_data = struct.unpack(f'<{number_of_audio_samples}d', parsable_file_in_ram)

left_channel = unpacked_audio_data[0::2]
right_channel = unpacked_audio_data[1::2]

step_table = [
    0.0000,
    0.0003,
    0.0007,
    0.0015,
    0.0031,
    0.0063,
    0.0127,
    0.0255,
    0.1020,
    0.2550,
    0.5610,
    1.1730,
    2.3970,
    4.8450,
    9.7410,
    19.533,
]

def main_encoder_math(sample_in_channel):
    current_sample_table_prediction = step_table[0]
    past_predicted_sample = 0.0
    undershooting_center_or_overshooting = None
    encoded_bits = []
    
    for current_sample in sample_in_channel:

        def prediction_machine(current_sample, current_sample_table_prediction):
        
            difference_between_guessed_and_current_sample = current_sample - current_sample_table_prediction
        
            if difference_between_guessed_and_current_sample >= 0: # 0 to 15
                calculated_direction_vector = 1

            elif difference_between_guessed_and_current_sample <= 1: # -15 to 1
                calculated_direction_vector = 0

            else:
                calculated_direction_vector = 0
            
            return calculated_direction_vector
            # if the "should go" vector is 0, we are overshooting, if 1, we are undershooting
        
        
        
        calculated_direction_vector = prediction_machine(current_sample, current_sample_table_prediction)
        crichur_count = 0
        write_bit_down_as = 0

        if undershooting_center_or_overshooting == 1 and calculated_direction_vector == 1 and crichur_count == 0:
            # We already went up before! We need to go up.
            while calculated_direction_vector == 1 and crichur_count < 15:
                crichur_count += 1
                current_sample_table_prediction = past_predicted_sample + step_table[crichur_count]
                calculated_direction_vector = prediction_machine(current_sample, current_sample_table_prediction)

                write_bit_down_as = 1
            past_predicted_sample = current_sample_table_prediction

        elif undershooting_center_or_overshooting == 0 and calculated_direction_vector == 0 and crichur_count == 0:
            # We already went down before! We need to go down. 
            # fixed a 1 but where calc was looking for 1 instead of 0
            while calculated_direction_vector == 0 and crichur_count < 15:
                crichur_count += 1
                current_sample_table_prediction = past_predicted_sample - step_table[crichur_count]
                calculated_direction_vector = prediction_machine(current_sample, current_sample_table_prediction)

            write_bit_down_as = 0
            past_predicted_sample = current_sample_table_prediction

        elif undershooting_center_or_overshooting == 1 and calculated_direction_vector == 0 and crichur_count == 0:
            # We already went up before! We need to go down.
            while calculated_direction_vector == 0 and crichur_count < 15:
                crichur_count += 1
                current_sample_table_prediction = past_predicted_sample - step_table[crichur_count]
                calculated_direction_vector = prediction_machine(current_sample, current_sample_table_prediction)

            write_bit_down_as = 0
            past_predicted_sample = current_sample_table_prediction
        
        elif undershooting_center_or_overshooting == 0 and calculated_direction_vector == 1 and crichur_count == 0:
            # We already went down before! We need to go up. # Wait what the fuck # Oh okay DOWN
            while calculated_direction_vector == 1 and crichur_count < 15:
                crichur_count += 1
                current_sample_table_prediction = past_predicted_sample + step_table[crichur_count]
                calculated_direction_vector = prediction_machine(current_sample, current_sample_table_prediction)

            write_bit_down_as = 1
            past_predicted_sample = current_sample_table_prediction

        elif undershooting_center_or_overshooting == None and calculated_direction_vector == 0 and crichur_count == 0:
            # Fresh start, no memory. We know that we should "go down" (0 = go down)
            while calculated_direction_vector == 0 and crichur_count < 15:
                crichur_count += 1
                current_sample_table_prediction = -step_table[crichur_count]
                calculated_direction_vector = prediction_machine(current_sample, current_sample_table_prediction)

            undershooting_center_or_overshooting = 0
            write_bit_down_as = 0
            #WRITE DOWN THIS SAMPLE AS THE PAST ONE PLEASE, MWAH 
            past_predicted_sample = current_sample_table_prediction

        elif undershooting_center_or_overshooting == None and calculated_direction_vector == 1 and crichur_count == 0:
            # Fresh start, no memory. We know that we should "go up" (1 = go up)
            while calculated_direction_vector == 1 and crichur_count < 15:
                crichur_count += 1
                current_sample_table_prediction = step_table[crichur_count]
                calculated_direction_vector = prediction_machine(current_sample, current_sample_table_prediction)

            undershooting_center_or_overshooting = 1
            write_bit_down_as = 1
            #WRITE DOWN THIS SAMPLE AS THE PAST ONE PLEASE, MWAH 
            past_predicted_sample = current_sample_table_prediction
        
        else:
            crichur_count = 0

        first_bit = write_bit_down_as
        index_position = crichur_count
   
        encoded_bits.append((first_bit, index_position))
    return encoded_bits

left_encoded_bits = main_encoder_math(left_channel)
right_encoded_bits = main_encoder_math(right_channel)

all_encoded_bits = []

min_length = min(len(left_encoded_bits), len(right_encoded_bits))

for i in range(min_length):
    all_encoded_bits.append(left_encoded_bits[i])
    all_encoded_bits.append(right_encoded_bits[i])

packed_bytes = bytearray()

for direction_bit, index_position in all_encoded_bits:
    byte_value = (direction_bit << 7) | (index_position << 3)
    
    packed_bytes.append(byte_value)

with open(output_filename, 'wb') as output_file:
    output_file.write(b'1P4-384000hz-2chan\n')
    output_file.write(packed_bytes)

print("Encoding complete. 1P4 is rawr.")
