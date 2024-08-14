import os
import re

# GO TO BOTTOM OF CODE FOR USAGE

def get_content(textfile_dir, textfile_name):
    with open(f"{textfile_dir}\\{textfile_name}") as f:
        content = f.readlines()

    return content


def init_file(content, dir):
    first_line_split = content[0].split()

    object_type = first_line_split[1]
    object_number = first_line_split[2]
    object_name = ' '.join(first_line_split[3:])
    output_directory = f"{os.path.abspath(os.path.join(os.getcwd(), os.pardir))}\\Onafgemaakte pagina\'s\\DEV_{object_number[2:]}-{object_name}.{object_type}.txt"
    
    with open(output_directory, "w") as f:
        f.write(f"{object_type.lower()} {object_number} \"{object_name}\"\n")
        f.write("{\n")

    generate_code(content, output_directory)


def generate_code(content, output_directory):
    generated_lines = []
    depth = 1
    field_mode = False

    line_number = 11
    while line_number < len(content)-1:
        line = content[line_number]

        # Fields
        if field_mode:
            if line.lstrip().startswith('{'):
                depth += 1
                field_lines, line = get_field(content, line_number)
                generated_lines.extend(field_lines)
        elif line.endswith("FIELDS\n"):
            generated_lines.pop() # Remove last closing bracket
            field_mode = True
            depth += 2
            line_number += 1
            generated_lines.extend(['', "    fields", "    {"])

        # Triggers
        if line.endswith("=BEGIN\n"):
            trigger_name = line.split('=')[0].strip()
            generated_lines.append(f"{'    '*(depth)}trigger {trigger_name}();")
            generated_lines.append('    '*depth + "BEGIN")
            line_number += 1
            trigger_lines, lines_read = get_block(content, line_number, depth+1)
            generated_lines.extend(trigger_lines)
            line_number += lines_read
        
        # CaptionML
        elif line.lstrip().startswith("CaptionML=") or line.lstrip().startswith("OptionCaptionML="):
            captionML_line, lines_read = get_captionML(line, content, line_number, depth)
            generated_lines.append(captionML_line)
            line_number += lines_read
        
        # OptionMembers
        elif line.lstrip().startswith("OptionString="):
            generated_lines.append(get_option_members(line, depth))
        
        # Other field properties
        elif line.find('=') > 0 and field_mode:
            other_property = line.strip(" }{\n;")
            if other_property:
                property_name, raw_value = other_property.split('=')
                if raw_value == "Yes":
                    property_value = "true"
                elif raw_value == "No":
                    property_value = "false"
                else:
                    property_value = raw_value
                generated_lines.append('    '*depth + f"{property_name} = {property_value};")
                if line.lstrip().startswith('{'):
                    line_number += 1

        # Keys
        elif line.endswith("KEYS\n"):
            generated_lines.extend(['', "    keys", '    {'])
            line_number += 2
            key_lines = get_keys(content, line_number)
            generated_lines.extend(key_lines)
            line_number += len(key_lines)
            depth += 1

        # Skips "FIELDGROUPS" and opening part of "CODE"
        elif content[line_number].endswith("FIELDGROUPS\n"):
            line_number += 5
        
        # Variables
        if content[line_number].endswith("VAR\n"):
            generated_lines.extend(['', "    "*depth + "var"])
            line_number += 1
            variable_lines = get_variables(content, line_number, depth)
            generated_lines.extend(variable_lines)
            line_number += len(variable_lines)-1
        
        # Procedures
        elif line.lstrip().startswith("PROCEDURE"):
            procedure_name = line.split()[1].strip()
            generated_lines.append('    '*depth + f"procedure {procedure_name}();")
            line_number += 1
            procedure_lines, number_of_lines_read = get_block(content, line_number, depth, 0)
            generated_lines.extend(procedure_lines)
            line_number += number_of_lines_read

        # Depth
        if content[line_number].lstrip().startswith('{'):
            if not field_mode:
                generated_lines.append('    '*depth + '{')
                depth += 1
        if content[line_number].endswith("}\n"):
            depth -= 1
            generated_lines.append('    '*depth + '}')

        # Disables field mode
        if depth == 1 and field_mode:
            field_mode = False
            line_number += 1
        
        else:
            line_number += 1
    
    with open(output_directory, "a") as f:
        f.writelines(gen_line + '\n' for gen_line in generated_lines)


def get_option_members(line, depth):
    option_members_raw = line.strip().split('=')[1].strip("}{];[")
    option_members_line = '    '*depth + 'OptionMembers = '
    option_members = []
    for option_member in option_members_raw.split(','):
        if option_member:
            option_members.append(f'"{option_member}"')
        else:
            option_members.append('')
    formatted_members = ','.join(option_members) + ';'
    option_members_line += formatted_members

    return option_members_line
    


def get_variables(content, line_number, depth):
    variable_lines = []
    local_iteration = line_number

    while ':' in (current_line := content[local_iteration].strip()):
        local_iteration += 1
        raw_name, raw_value = current_line.split(':')
        variable_name = raw_name.split('@')[0]
        variable_value = raw_value.strip()
        variable_lines.append("    "*depth + f"    {variable_name} : {variable_value}")
    variable_lines.append('')

    return variable_lines
    

def get_keys(content, line_number):
    key_lines = []
    local_iteration = 0
    
    line = content[line_number].strip()
    while not line == "}":
        local_iteration += 1
        key_items = [x.strip() for x in line.strip("}{").split(";")[1:]]
        line = content[line_number + local_iteration].strip()
        current_key = f'        key(key{local_iteration};'

        fields = []
        for field in key_items[0].split(','):
            fields.append(f'"{field}"')
        formatted_fields = ','.join(fields)
        current_key += formatted_fields + ") {"

        if len(key_items) >= 2:
            for property_item in key_items[1:]:
                key_property, raw_value = property_item.split('=')
                if raw_value == "Yes":
                    key_value = "true"
                elif raw_value == "No":
                    key_value = "false"
                else:
                    key_value = raw_value
                current_key += f" {key_property} = {key_value};"
            current_key += " }"
        else:
            current_key += '}'
                
        key_lines.append(current_key)
    
    return key_lines


def get_field(content, line_number):
    field_lines = []

    line = content[line_number]
    field_id = line.split(';')[0].strip(' {')
    field_name = line.split(';')[2].strip()
    raw_type = line.split(';')[3].strip()
    line_body = line.split(';')[4].strip()

    raw_type = re.split('(\d+)', raw_type)
    if len(raw_type) > 1:
        field_type = f"{raw_type[0]}[{raw_type[1]}]"
    else:
        field_type = raw_type[0]

    # First line and opening bracket
    field_lines.append(f'        field({field_id}; "{field_name}"; {field_type})')
    field_lines.append('        {')

    return field_lines, line_body + ';'


def get_captionML(first_line, content, line_number, depth):
    caption_line = None
    number_of_lines_read = 0
    term_used, current_language, current_definition = [x.strip('[]') for x in first_line.strip(" ;\n").split('=')]

    caption_line = '    '*depth + f"{term_used} = {current_language} = '{current_definition}', " # First caption line
    if first_line.endswith("];\n"):
        return caption_line, 1

    while True:
        number_of_lines_read += 1
        current_line = content[line_number + number_of_lines_read]
        current_language, current_definition = current_line.strip("} \n];").split('=')
        caption_line += f"{current_language} = '{current_definition}'"

        if current_line.strip(" }\n").endswith("];") or current_line.strip(" }\n").endswith("]"):
            break
    
    caption_line += ';'
    
    return caption_line, number_of_lines_read


def get_block(content, line_number, depth, begins = 1):
    trigger_lines = []
    number_of_lines_read = 0
    internal_depth = depth
    
    ends_needed = begins
    while True:
        current_line = content[line_number+number_of_lines_read]
        if current_line.endswith("BEGIN\n"):
            ends_needed += 1
            trigger_lines.append(f"{'    '*internal_depth}{current_line.strip()}")
            internal_depth += 1
        elif current_line.endswith("END;\n"):
            ends_needed -= 1
            internal_depth -= 1
            trigger_lines.append(f"{'    '*internal_depth}END;")
            if ends_needed == 0:
                break
        elif current_line.endswith("END\n"):
            ends_needed -= 1
            internal_depth -= 1
            trigger_lines.append(f"{'    '*internal_depth}END")
        else:
            trigger_lines.append(f"{'    '*internal_depth}{current_line.strip()}")
        
        number_of_lines_read += 1
    
    trigger_lines.append('')
    return trigger_lines, number_of_lines_read


if __name__ == "__main__":
    my_dir = "C:\SMensing\Tickets met relevante files\HST-1720 (Tabellen ombouwen naar nieuwe omgeving)"
    # content = get_content(my_dir, "11014354 Table Txt CAL code.txt")
    # init_file(content, my_dir)
    for table_number in list(range(11014350,11014358)) + list(range(11014360, 11014368)):
        content = get_content(my_dir, f"{table_number} Table Txt CAL code.txt")
        init_file(content, my_dir)