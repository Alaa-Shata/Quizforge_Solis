import sqlite3
from database.connection import get_connection


QUESTION_BANK = {

    "Cybersecurity": [
        # EASY
        (1, "Which security principle gives users only the permissions they need?",
         ["Least Privilege", "Open Access", "Full Control", "Shared Access"],
         "A", "Least Privilege limits permissions to what is necessary."),

        (1, "What is the main purpose of a firewall?",
         ["Encrypt files", "Filter network traffic", "Create passwords", "Remove viruses"],
         "B", "A firewall filters incoming and outgoing network traffic."),

        (1, "Which password is the strongest?",
         ["12345678", "password", "R7#mP9!qL2", "john2026"],
         "C", "A long, random password with mixed characters is harder to guess."),

        (1, "What does phishing attempt to steal?",
         ["Screen resolution", "Personal information", "CPU performance", "Disk space"],
         "B", "Phishing tricks users into revealing sensitive information."),

        (1, "Which protocol secures web communication?",
         ["HTTP", "FTP", "HTTPS", "Telnet"],
         "C", "HTTPS uses TLS to protect communication between browsers and servers."),

        (1, "What should you do with an unexpected email attachment?",
         ["Open it immediately", "Forward it to everyone", "Verify the sender first", "Disable antivirus"],
         "C", "Unexpected attachments should be verified before opening."),

        (1, "What is malware?",
         ["A hardware component", "Malicious software", "A backup method", "A network cable"],
         "B", "Malware is software designed to harm systems or perform unauthorized actions."),

        (1, "What is the purpose of antivirus software?",
         ["Increase internet speed", "Detect and remove malicious software", "Create accounts", "Manage databases"],
         "B", "Antivirus software detects and helps remove malware."),

        (1, "Which method adds an extra authentication factor?",
         ["Using the same password twice", "Multi-factor authentication", "Disabling login", "Sharing credentials"],
         "B", "MFA requires additional evidence of identity beyond a password."),

        (1, "Why should operating systems receive security updates?",
         ["To change the desktop wallpaper", "To fix vulnerabilities", "To delete user accounts", "To reduce screen brightness"],
         "B", "Security updates patch known vulnerabilities."),

        # MEDIUM
        (2, "A user receives a fake login page that copies a bank website. What attack is this?",
         ["Phishing", "DDoS", "SQL injection", "Brute-force attack"],
         "A", "The fake page attempts to steal login credentials through deception."),

        (2, "Which technique helps protect stored passwords?",
         ["Plain-text storage", "Password hashing with salt", "Sending passwords by email", "Using reversible encoding"],
         "B", "Salted password hashing makes stolen password databases harder to exploit."),

        (2, "An application inserts user input directly into an SQL query. What is the main risk?",
         ["SQL injection", "Packet sniffing", "Shoulder surfing", "Ransomware"],
         "A", "Untrusted input can alter the meaning of an SQL query."),

        (2, "Which control helps detect suspicious activity after it occurs?",
         ["Audit logging", "Screen locking only", "File compression", "Disk formatting"],
         "A", "Audit logs record events that can be reviewed during investigations."),

        (2, "What is the main purpose of network segmentation?",
         ["Increase password length", "Limit movement between network areas", "Disable encryption", "Remove authentication"],
         "B", "Segmentation restricts communication and can limit lateral movement."),

        (2, "A company wants to ensure transmitted data cannot be easily read by attackers. What should it use?",
         ["Encryption", "Compression", "Formatting", "Defragmentation"],
         "A", "Encryption protects data confidentiality during transmission."),

        (2, "Which attack repeatedly tries many password combinations?",
         ["Brute-force attack", "Phishing", "DNS poisoning", "Tailgating"],
         "A", "A brute-force attack attempts multiple possible passwords."),

        (2, "What does the principle of defense in depth mean?",
         ["Using one strong firewall only", "Using multiple layers of security controls", "Removing all user accounts", "Avoiding security monitoring"],
         "B", "Multiple defensive layers reduce reliance on a single control."),

        (2, "Why are parameterized SQL queries recommended?",
         ["They make queries longer", "They help prevent SQL injection", "They disable database permissions", "They remove database indexes"],
         "B", "Parameters separate user input from SQL command structure."),

        (2, "A security team observes many failed login attempts from one IP address. What should it investigate?",
         ["Possible brute-force activity", "Printer configuration", "Monitor resolution", "Disk fragmentation"],
         "A", "Repeated failed logins may indicate password-guessing attempts."),

        # HARD
        (3, "A web application uses prepared statements but displays untrusted input without encoding. Which vulnerability may remain?",
         ["Cross-site scripting", "ARP spoofing", "DDoS", "Port scanning"],
         "A", "Prepared statements address SQL injection, while output encoding helps prevent XSS."),

        (3, "An attacker steals a valid session cookie. Which attack can this enable?",
         ["Session hijacking", "Password spraying", "DNS enumeration", "Data compression"],
         "A", "A stolen valid session token may allow an attacker to impersonate the user."),

        (3, "Which control best limits the impact of a compromised employee account?",
         ["Least privilege and access segmentation", "Shared administrator accounts", "Disabling audit logs", "Permanent unrestricted access"],
         "A", "Restricted permissions and segmentation reduce what a compromised account can access."),

        (3, "A company needs to verify that a downloaded software package has not been modified. What should it verify?",
         ["A trusted digital signature", "The file name only", "The download speed", "The screen size"],
         "A", "A trusted digital signature can verify integrity and publisher authenticity."),

        (3, "Why is a cryptographic hash alone insufficient to prove who created a file?",
         ["Hashes are always reversible", "Anyone can calculate a hash", "Hashes require a password", "Hashes only work on images"],
         "B", "A hash can detect changes, but by itself does not authenticate its creator."),

        (3, "An attacker gains access to one workstation and attempts to access other internal systems. What is this movement called?",
         ["Lateral movement", "Data normalization", "Load balancing", "Code compilation"],
         "A", "Lateral movement describes moving through a compromised environment."),

        (3, "Which approach is most appropriate for protecting encryption keys?",
         ["Store them beside encrypted files", "Use a dedicated key-management system", "Publish them in source code", "Reuse one key forever"],
         "B", "Dedicated key management protects, controls, and rotates cryptographic keys."),

        (3, "A company detects an intrusion but has no reliable event records. Which security capability is most directly weakened?",
         ["Incident investigation", "Data compression", "User interface design", "Network addressing"],
         "A", "Without logs, reconstructing attacker actions becomes difficult."),

        (3, "What is the main security benefit of rotating compromised credentials?",
         ["It invalidates exposed credentials", "It increases screen resolution", "It disables encryption", "It removes database indexes"],
         "A", "Replacing compromised credentials prevents continued use of the exposed secrets."),

        (3, "A server accepts expired certificates without warning. Which security property is weakened?",
         ["Trust in endpoint authentication", "Data compression", "Storage capacity", "CPU scheduling"],
         "A", "Certificate validation helps establish the identity of the communicating endpoint."),
    ],

    "Networking": [
        # EASY
        (1, "Which device connects different networks and forwards packets between them?",
         ["Router", "Switch", "Keyboard", "Repeater"],
         "A", "A router forwards packets between different networks."),

        (1, "Which protocol translates domain names into IP addresses?",
         ["DNS", "FTP", "SMTP", "SSH"],
         "A", "DNS resolves domain names to IP addresses."),

        (1, "Which protocol provides reliable, connection-oriented transport?",
         ["UDP", "TCP", "IP", "ARP"],
         "B", "TCP provides reliable, ordered data delivery."),

        (1, "What does an IP address identify?",
         ["A network interface logically", "A file extension", "A browser tab", "A keyboard layout"],
         "A", "An IP address provides logical addressing for network communication."),

        (1, "Which device commonly connects devices within a local area network?",
         ["Switch", "Modem only", "Printer", "Scanner"],
         "A", "A switch forwards Ethernet frames within a LAN."),

        (1, "Which protocol automatically assigns IP configuration to clients?",
         ["DHCP", "HTTP", "FTP", "SNMP"],
         "A", "DHCP automatically provides IP addresses and related configuration."),

        (1, "Which protocol is commonly used to access websites?",
         ["HTTP", "SMTP", "POP3", "SSH"],
         "A", "HTTP is used for communication between web clients and servers."),

        (1, "What does LAN stand for?",
         ["Local Area Network", "Large Access Node", "Logical Address Number", "Long Area Network"],
         "A", "A LAN connects devices within a limited geographical area."),

        (1, "Which protocol is commonly used to send email between mail servers?",
         ["SMTP", "DNS", "DHCP", "ARP"],
         "A", "SMTP is used to send email between mail servers."),

        (1, "What is the main function of a network cable?",
         ["Carry data signals", "Encrypt passwords", "Assign IP addresses", "Resolve domain names"],
         "A", "Network cables provide a physical medium for data transmission."),

        # MEDIUM
        (2, "Which transport protocol is generally preferred for real-time voice communication where low delay matters?",
         ["UDP", "TCP", "FTP", "SMTP"],
         "A", "UDP avoids retransmission delays and is often used for real-time traffic."),

        (2, "A host has IP address 192.168.1.10/24. What is its network address?",
         ["192.168.1.0", "192.168.1.10", "192.168.1.255", "192.168.0.10"],
         "A", "A /24 subnet uses 255.255.255.0, making the network address 192.168.1.0."),

        (2, "What is the purpose of a default gateway?",
         ["Forward traffic to other networks", "Translate domain names", "Assign MAC addresses", "Encrypt application data"],
         "A", "A default gateway forwards traffic destined outside the local network."),

        (2, "Which protocol maps an IPv4 address to a MAC address on a local network?",
         ["ARP", "DNS", "DHCP", "TLS"],
         "A", "ARP discovers the MAC address associated with a local IPv4 address."),

        (2, "What does a VLAN primarily provide?",
         ["Logical network segmentation", "Faster CPU processing", "Automatic encryption of all files", "Domain name registration"],
         "A", "VLANs separate broadcast domains logically on switching infrastructure."),

        (2, "Which TCP feature helps ensure data arrives in the correct order?",
         ["Sequence numbers", "DNS records", "MAC filtering", "VLAN tags"],
         "A", "TCP sequence numbers support ordered data reconstruction."),

        (2, "What is the main purpose of NAT in many private networks?",
         ["Translate private and public IP addresses", "Encrypt wireless passwords", "Resolve hostnames", "Detect viruses"],
         "A", "NAT translates addresses between internal and external networks."),

        (2, "Which tool is commonly used to test basic IP reachability?",
         ["ping", "format", "mkdir", "chmod"],
         "A", "Ping sends ICMP echo requests to test reachability."),

        (2, "A DNS server returns an incorrect address for a domain. Which attack may be involved?",
         ["DNS spoofing", "SYN flooding", "Password spraying", "Buffer overflow"],
         "A", "DNS spoofing manipulates DNS responses to direct users to incorrect destinations."),

        (2, "Which OSI layer is responsible for routing packets between networks?",
         ["Network layer", "Physical layer", "Presentation layer", "Session layer"],
         "A", "The OSI Network layer handles logical addressing and routing."),

        # HARD
        (3, "During a TCP three-way handshake, which sequence is correct?",
         ["SYN, SYN-ACK, ACK", "ACK, FIN, SYN", "SYN, ACK, FIN", "FIN, SYN, SYN-ACK"],
         "A", "TCP establishes a connection using SYN, SYN-ACK, and ACK."),

        (3, "A network uses the subnet mask 255.255.255.192. How many usable host addresses are available per subnet?",
         ["30", "62", "126", "254"],
         "B", "A /26 subnet has 64 addresses, with 62 usable host addresses."),

        (3, "Which attack overwhelms a server with large volumes of traffic from multiple sources?",
         ["Distributed denial of service", "ARP resolution", "DNS caching", "Port forwarding"],
         "A", "A DDoS attack uses multiple sources to overwhelm a target."),

        (3, "Why does TCP use acknowledgments?",
         ["To confirm received data", "To assign MAC addresses", "To resolve domain names", "To encrypt IP headers"],
         "A", "Acknowledgments allow TCP to track successful data reception."),

        (3, "A switch receives a frame with an unknown destination MAC address. What does it normally do?",
         ["Flood it within the VLAN", "Drop every frame", "Send it to the DNS server", "Convert it to an IP packet"],
         "A", "A switch floods unknown unicast frames to ports in the same VLAN except the incoming port."),

        (3, "Which routing protocol is commonly used between autonomous systems on the Internet?",
         ["BGP", "OSPF", "RIP", "ARP"],
         "A", "BGP exchanges routing information between autonomous systems."),

        (3, "What is the main purpose of TLS in network communication?",
         ["Provide confidentiality and integrity", "Assign private IP addresses", "Route packets", "Resolve MAC addresses"],
         "A", "TLS protects communication through encryption and integrity checks."),

        (3, "What is the effect of a /30 IPv4 subnet in traditional point-to-point addressing?",
         ["Two usable host addresses", "Four usable host addresses", "Thirty usable host addresses", "Sixty-two usable host addresses"],
         "A", "A /30 subnet contains four addresses, traditionally two usable host addresses."),

        (3, "Which mechanism helps prevent switching loops in Ethernet networks?",
         ["Spanning Tree Protocol", "Dynamic DNS", "FTP", "DHCP"],
         "A", "STP prevents Layer 2 loops by blocking selected redundant paths."),

        (3, "A router chooses between routes to the same destination prefix. Which value is commonly considered first in longest-prefix routing?",
         ["Prefix length", "MAC address length", "DNS TTL", "TCP window size"],
         "A", "Routers generally prefer the route with the longest matching prefix."),
    ],

    "Python": [
        # EASY
        (1, "Which keyword is used to define a function in Python?",
         ["func", "define", "def", "function"],
         "C", "The def keyword defines a function in Python."),

        (1, "Which data type stores True or False?",
         ["str", "bool", "list", "dict"],
         "B", "The bool type represents Boolean values True and False."),

        (1, "What is the result of 10 // 3?",
         ["3", "3.33", "1", "4"],
         "A", "The // operator performs floor division."),

        (1, "Which symbol starts a single-line comment in Python?",
         ["//", "#", "/*", "--"],
         "B", "Python uses # for single-line comments."),

        (1, "Which collection stores ordered, changeable elements?",
         ["tuple", "list", "frozenset", "str"],
         "B", "Lists are ordered and mutable collections."),

        (1, "What does len([4, 7, 9]) return?",
         ["2", "3", "4", "9"],
         "B", "The list contains three elements."),

        (1, "Which method adds an item to the end of a list?",
         ["append()", "remove()", "sort()", "clear()"],
         "A", "append() adds one element to the end of a list."),

        (1, "What is the output of print(2 ** 3)?",
         ["5", "6", "8", "9"],
         "C", "The ** operator performs exponentiation: 2 raised to 3 is 8."),

        (1, "Which brackets are used to create a dictionary?",
         ["[]", "()", "{}", "<>"],
         "C", "Dictionaries are created using curly braces with key-value pairs."),

        (1, "Which function converts a value to an integer when possible?",
         ["str()", "int()", "float()", "bool()"],
         "B", "int() converts a compatible value to an integer."),

        # MEDIUM
        (2, "What is the output of [x * 2 for x in [1, 2, 3]]?",
         ["[1, 2, 3]", "[2, 4, 6]", "[1, 4, 9]", "[2, 3, 4]"],
         "B", "The list comprehension doubles each element."),

        (2, "What does dict.get('age') return if the key does not exist and no default is provided?",
         ["0", "False", "None", "KeyError"],
         "C", "get() returns None by default when the key is missing."),

        (2, "Which statement is used to handle exceptions?",
         ["if/else", "try/except", "for/in", "with/as"],
         "B", "try/except handles exceptions raised during execution."),

        (2, "What is the main purpose of the with statement when opening a file?",
         ["Automatically manage resource cleanup", "Encrypt the file", "Sort file contents", "Create a database"],
         "A", "A context manager closes the file automatically when the block exits."),

        (2, "What does range(2, 6) generate?",
         ["2, 3, 4, 5", "2, 3, 4, 5, 6", "1, 2, 3, 4, 5", "6, 5, 4, 3, 2"],
         "A", "The stop value is excluded, so the sequence ends at 5."),

        (2, "What is the output of 'Python'.lower()?",
         ["PYTHON", "python", "Python", "pYTHON"],
         "B", "lower() returns a lowercase version of the string."),

        (2, "Which operator checks whether two values are equal?",
         ["=", "==", "!=", ":="],
         "B", "The == operator compares values for equality."),

        (2, "What does enumerate() provide when iterating over a sequence?",
         ["Only values", "Index and value pairs", "Only indexes", "Sorted values"],
         "B", "enumerate() yields pairs containing an index and its corresponding value."),

        (2, "What happens when a function reaches the end without a return statement?",
         ["Returns 0", "Returns None", "Raises SyntaxError", "Returns False"],
         "B", "Python functions return None implicitly when no return value is specified."),

        (2, "Which data structure automatically removes duplicate elements?",
         ["list", "tuple", "set", "str"],
         "C", "A set stores unique elements."),

        # HARD
        (3, "What is the output of this code: x = [1, 2]; y = x; y.append(3); print(x)?",
         ["[1, 2]", "[1, 2, 3]", "[3]", "Error"],
         "B", "Both variables reference the same list object."),

        (3, "What is the purpose of __init__ in a Python class?",
         ["Destroy an object", "Initialize a new object", "Import a module", "Handle exceptions"],
         "B", "__init__ initializes instance attributes when an object is created."),

        (3, "What does a decorator typically do?",
         ["Modify or extend a function's behavior", "Delete a Python module", "Convert all values to strings", "Stop program execution"],
         "A", "A decorator wraps a callable to add or modify behavior."),

        (3, "What is the main difference between a generator and a list?",
         ["Generators produce values lazily", "Lists cannot store integers", "Generators are always faster", "Lists cannot be iterated"],
         "A", "Generators yield values on demand instead of storing all results at once."),

        (3, "What does the finally block guarantee in a try/except structure?",
         ["It runs only when an exception occurs", "It normally runs whether or not an exception occurs", "It runs before try", "It prevents all exceptions"],
         "B", "finally is used for cleanup and normally executes regardless of exceptions."),

        (3, "What is the output of bool([])?",
         ["True", "False", "None", "TypeError"],
         "B", "An empty list is falsy in Python."),

        (3, "Why should mutable default arguments generally be avoided?",
         ["They are recreated on every call", "They may retain changes between calls", "They cannot store values", "They cause syntax errors"],
         "B", "A mutable default object is created once and can be shared across calls."),

        (3, "What does super() commonly allow a class to do?",
         ["Call methods from its parent class", "Delete its parent class", "Create a global variable", "Disable inheritance"],
         "A", "super() provides access to methods in the method resolution order."),

        (3, "What is the output of list(zip([1, 2], ['a', 'b']))?",
         ["[(1, 'a'), (2, 'b')]", "[1, 2, 'a', 'b']", "[(1, 2), ('a', 'b')]", "Error"],
         "A", "zip() pairs corresponding elements from the input iterables."),

        (3, "What is the purpose of __name__ == '__main__'?",
         ["Run code only when the module is executed directly", "Import every installed package", "Define a class constructor", "Stop a running loop"],
         "A", "The condition distinguishes direct execution from importing a module."),
    ],
}


def _normalize_text(text: str) -> str:
    return " ".join(text.strip().split()).lower()


def seed_database():
    conn = get_connection()

    try:
        with conn:
            inserted_count = 0
            synced_existing_count = 0

            for topic_name, questions in QUESTION_BANK.items():
                conn.execute(
                    "INSERT OR IGNORE INTO topics (name) VALUES (?)",
                    (topic_name,)
                )
                row = conn.execute(
                    "SELECT id FROM topics WHERE name = ?",
                    (topic_name,)
                ).fetchone()

                if row is None:
                    raise ValueError(f"Topic not found or could not be created: {topic_name}")

                topic_id = row["id"]

                for difficulty, question, options, correct, explanation in questions:
                    normalized_q = _normalize_text(question)
                    existing = conn.execute(
                        """
                        SELECT id FROM questions
                        WHERE topic_id = ? AND lower(trim(text)) = ?
                        """,
                        (topic_id, normalized_q)
                    ).fetchone()

                    if existing is not None:
                        conn.execute(
                            """
                            UPDATE questions
                            SET text = ?, option_a = ?, option_b = ?, option_c = ?,
                                option_d = ?, correct_option = ?, difficulty = ?,
                                explanation = ?, is_active = 1
                            WHERE id = ?
                            """,
                            (
                                question,
                                options[0],
                                options[1],
                                options[2],
                                options[3],
                                correct,
                                difficulty,
                                explanation,
                                existing["id"],
                            )
                        )
                        synced_existing_count += 1
                    else:
                        conn.execute(
                            """
                            INSERT INTO questions
                            (topic_id, text, option_a, option_b, option_c,
                             option_d, correct_option, difficulty,
                             explanation, is_active)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
                            """,
                            (
                                topic_id,
                                question,
                                options[0],
                                options[1],
                                options[2],
                                options[3],
                                correct,
                                difficulty,
                                explanation,
                            )
                        )
                        inserted_count += 1

            print(
                f"Seed completed safely: {inserted_count} inserted, "
                f"{synced_existing_count} existing synced without duplicates."
            )

    finally:
        conn.close()


if __name__ == "__main__":
    seed_database()