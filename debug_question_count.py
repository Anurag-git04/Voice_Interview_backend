"""
Debug script to understand question counting logic.
Run this to see what's happening with turn counts.
"""

# Simulate the flow for a 5-question interview

def count_main_questions(turns):
    """Each turn = 1 Q&A pair"""
    return len(turns)

def simulate_interview(max_questions=5):
    print(f"\n=== SIMULATING {max_questions}-QUESTION INTERVIEW ===\n")
    
    # Start: Create session and generate first question
    print("STEP 0: Create session")
    print("  → First question generated")
    print("  → Database has 1 turn (with question, no answer yet)\n")
    
    # User answers questions
    for i in range(1, max_questions + 2):  # Go one extra to see when it stops
        print(f"STEP {i}: User submits answer to question {i}")
        
        # After user submits, the turn gets the answer
        turns_count = i  # Now we have i turns with both Q&A
        
        print(f"  → Database now has {turns_count} turns (all answered)")
        print(f"  → Call generate_next_question with turns={turns_count}")
        
        question_count = count_main_questions(range(turns_count))
        print(f"  → question_count = {question_count}")
        print(f"  → Check: {question_count} >= {max_questions}? ", end="")
        
        if question_count >= max_questions:
            print("YES → Interview complete ✅")
            print(f"  → Total questions asked: {question_count}")
            break
        else:
            print("NO → Generate next question")
            print(f"  → Will generate question #{question_count + 1}\n")

if __name__ == "__main__":
    simulate_interview(5)
    print("\n" + "="*60 + "\n")
    simulate_interview(3)
