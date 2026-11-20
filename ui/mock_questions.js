/* ======================================================
   QUIZFORGE - MOCK DATA
   DEVELOPMENT ONLY

   Replace this file's data source when the real
   Question Bank integration is approved.

   This file does NOT create database records.
   ====================================================== */

window.QUIZ_MOCK_DATA = {

    topics: [
        { id: "networking", name: "Networking" },
        { id: "cryptography", name: "Cryptography" },
        { id: "python", name: "Python" }
    ],

    questions: [

        // NETWORKING - 10 QUESTIONS

        {
            id: "net-01",
            topic_id: "networking",
            question: "Which protocol is used to securely browse websites?",
            options: {
                A: "HTTP",
                B: "HTTPS",
                C: "FTP",
                D: "SMTP"
            },
            correct_answer: "B",
            explanation: "HTTPS uses encryption through TLS to secure communication."
        },

        {
            id: "net-02",
            topic_id: "networking",
            question: "Which transport protocol provides reliable data delivery?",
            options: {
                A: "UDP",
                B: "IP",
                C: "TCP",
                D: "ARP"
            },
            correct_answer: "C",
            explanation: "TCP provides reliable, ordered data delivery."
        },

        {
            id: "net-03",
            topic_id: "networking",
            question: "What is the primary function of DNS?",
            options: {
                A: "Encrypt files",
                B: "Translate domain names into IP addresses",
                C: "Assign MAC addresses",
                D: "Block network traffic"
            },
            correct_answer: "B",
            explanation: "DNS resolves human-readable domain names into IP addresses."
        },

        {
            id: "net-04",
            topic_id: "networking",
            question: "Which device forwards packets between different networks?",
            options: {
                A: "Switch",
                B: "Hub",
                C: "Router",
                D: "Repeater"
            },
            correct_answer: "C",
            explanation: "A router forwards packets between different networks."
        },

        {
            id: "net-05",
            topic_id: "networking",
            question: "Which protocol automatically assigns IP addresses?",
            options: {
                A: "DHCP",
                B: "DNS",
                C: "FTP",
                D: "SSH"
            },
            correct_answer: "A",
            explanation: "DHCP automatically provides network configuration to devices."
        },

        {
            id: "net-06",
            topic_id: "networking",
            question: "Which protocol is commonly used to send emails?",
            options: {
                A: "POP3",
                B: "SMTP",
                C: "DNS",
                D: "ARP"
            },
            correct_answer: "B",
            explanation: "SMTP is commonly used for sending email messages."
        },

        {
            id: "net-07",
            topic_id: "networking",
            question: "What does an IP address identify?",
            options: {
                A: "A device's network interface logically",
                B: "A user's password",
                C: "A file extension",
                D: "A website's HTML structure"
            },
            correct_answer: "A",
            explanation: "An IP address is a logical address used to identify a network interface."
        },

        {
            id: "net-08",
            topic_id: "networking",
            question: "Which protocol is connectionless?",
            options: {
                A: "TCP",
                B: "UDP",
                C: "HTTPS",
                D: "SSH"
            },
            correct_answer: "B",
            explanation: "UDP sends datagrams without establishing a connection."
        },

        {
            id: "net-09",
            topic_id: "networking",
            question: "Which port is the default port for HTTPS?",
            options: {
                A: "21",
                B: "25",
                C: "80",
                D: "443"
            },
            correct_answer: "D",
            explanation: "HTTPS commonly uses TCP port 443."
        },

        {
            id: "net-10",
            topic_id: "networking",
            question: "What does a firewall primarily do?",
            options: {
                A: "Manage database tables",
                B: "Filter network traffic",
                C: "Compress files",
                D: "Translate programming languages"
            },
            correct_answer: "B",
            explanation: "A firewall filters network traffic according to security rules."
        },


        // CRYPTOGRAPHY - 10 QUESTIONS

        {
            id: "crypto-01",
            topic_id: "cryptography",
            question: "Which type of encryption uses the same key for encryption and decryption?",
            options: {
                A: "Asymmetric encryption",
                B: "Symmetric encryption",
                C: "Hashing",
                D: "Digital signatures"
            },
            correct_answer: "B",
            explanation: "Symmetric encryption uses the same secret key for both operations."
        },

        {
            id: "crypto-02",
            topic_id: "cryptography",
            question: "Which algorithm is a cryptographic hash function?",
            options: {
                A: "AES",
                B: "RSA",
                C: "SHA-256",
                D: "DES"
            },
            correct_answer: "C",
            explanation: "SHA-256 generates a fixed-length cryptographic hash."
        },

        {
            id: "crypto-03",
            topic_id: "cryptography",
            question: "What is the main purpose of encryption?",
            options: {
                A: "Confidentiality",
                B: "Data compression",
                C: "Increasing file size",
                D: "Removing duplicates"
            },
            correct_answer: "A",
            explanation: "Encryption protects confidentiality by making data unreadable without the appropriate key."
        },

        {
            id: "crypto-04",
            topic_id: "cryptography",
            question: "Which algorithm is commonly used for asymmetric encryption?",
            options: {
                A: "AES",
                B: "RSA",
                C: "SHA-256",
                D: "MD5"
            },
            correct_answer: "B",
            explanation: "RSA is a widely known public-key cryptographic algorithm."
        },

        {
            id: "crypto-05",
            topic_id: "cryptography",
            question: "What does a digital signature primarily provide?",
            options: {
                A: "Authentication and integrity",
                B: "Data compression",
                C: "Faster internet",
                D: "File recovery"
            },
            correct_answer: "A",
            explanation: "Digital signatures help verify authenticity and message integrity."
        },

        {
            id: "crypto-06",
            topic_id: "cryptography",
            question: "What is a plaintext?",
            options: {
                A: "Encrypted information",
                B: "Original readable information",
                C: "A private key",
                D: "A hash digest"
            },
            correct_answer: "B",
            explanation: "Plaintext is the original readable data before encryption."
        },

        {
            id: "crypto-07",
            topic_id: "cryptography",
            question: "Which algorithm is designed for symmetric encryption?",
            options: {
                A: "RSA",
                B: "AES",
                C: "SHA-1",
                D: "DSA"
            },
            correct_answer: "B",
            explanation: "AES is a symmetric block cipher."
        },

        {
            id: "crypto-08",
            topic_id: "cryptography",
            question: "What is the main purpose of a cryptographic hash?",
            options: {
                A: "Generate a fixed-size digest",
                B: "Decrypt ciphertext",
                C: "Exchange public keys",
                D: "Create network routes"
            },
            correct_answer: "A",
            explanation: "A cryptographic hash maps input data to a fixed-size digest."
        },

        {
            id: "crypto-09",
            topic_id: "cryptography",
            question: "In public-key cryptography, which key is shared publicly?",
            options: {
                A: "Private key",
                B: "Secret key",
                C: "Public key",
                D: "Session password"
            },
            correct_answer: "C",
            explanation: "The public key can be shared, while the private key must remain secret."
        },

        {
            id: "crypto-10",
            topic_id: "cryptography",
            question: "Which security property ensures data has not been modified?",
            options: {
                A: "Availability",
                B: "Integrity",
                C: "Confidentiality",
                D: "Scalability"
            },
            correct_answer: "B",
            explanation: "Integrity ensures that information has not been altered improperly."
        },


        // PYTHON - 10 QUESTIONS

        {
            id: "python-01",
            topic_id: "python",
            question: "Which keyword is used to define a function in Python?",
            options: {
                A: "function",
                B: "define",
                C: "def",
                D: "func"
            },
            correct_answer: "C",
            explanation: "Python uses the def keyword to define functions."
        },

        {
            id: "python-02",
            topic_id: "python",
            question: "Which data type stores True or False?",
            options: {
                A: "str",
                B: "bool",
                C: "list",
                D: "dict"
            },
            correct_answer: "B",
            explanation: "The bool type represents Boolean values: True and False."
        },

        {
            id: "python-03",
            topic_id: "python",
            question: "What is the result of 5 // 2?",
            options: {
                A: "2",
                B: "2.5",
                C: "3",
                D: "1"
            },
            correct_answer: "A",
            explanation: "The // operator performs floor division."
        },

        {
            id: "python-04",
            topic_id: "python",
            question: "Which collection is immutable?",
            options: {
                A: "List",
                B: "Dictionary",
                C: "Set",
                D: "Tuple"
            },
            correct_answer: "D",
            explanation: "Tuples are immutable collections in Python."
        },

        {
            id: "python-05",
            topic_id: "python",
            question: "Which method adds an item to the end of a list?",
            options: {
                A: "append()",
                B: "add()",
                C: "insert_end()",
                D: "push_back()"
            },
            correct_answer: "A",
            explanation: "append() adds an element to the end of a Python list."
        },

        {
            id: "python-06",
            topic_id: "python",
            question: "What does len() return?",
            options: {
                A: "The data type",
                B: "The number of items",
                C: "The memory address",
                D: "The largest value"
            },
            correct_answer: "B",
            explanation: "len() returns the number of items in an object."
        },

        {
            id: "python-07",
            topic_id: "python",
            question: "Which symbol starts a comment in Python?",
            options: {
                A: "//",
                B: "/*",
                C: "#",
                D: "--"
            },
            correct_answer: "C",
            explanation: "A # symbol starts a single-line comment in Python."
        },

        {
            id: "python-08",
            topic_id: "python",
            question: "Which keyword is used for conditional branching?",
            options: {
                A: "if",
                B: "repeat",
                C: "switch",
                D: "when"
            },
            correct_answer: "A",
            explanation: "Python uses if, elif, and else for conditional branching."
        },

        {
            id: "python-09",
            topic_id: "python",
            question: "Which structure stores key-value pairs?",
            options: {
                A: "Tuple",
                B: "Dictionary",
                C: "String",
                D: "Integer"
            },
            correct_answer: "B",
            explanation: "A dictionary stores data as key-value pairs."
        },

        {
            id: "python-10",
            topic_id: "python",
            question: "Which keyword is used to create a class?",
            options: {
                A: "object",
                B: "struct",
                C: "class",
                D: "new"
            },
            correct_answer: "C",
            explanation: "Python uses the class keyword to define a class."
        }

    ]

};