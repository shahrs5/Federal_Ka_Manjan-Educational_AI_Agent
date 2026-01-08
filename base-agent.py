#!/usr/bin/env python3
"""
Ultra-Simple Agent Core with SPOAR Loop

A minimal, extensible AI agent implementation using the SENSE-PLAN-ACT-OBSERVE-REFLECT pattern.

Model: openai/gpt-oss-120b (via Groq Cloud)

Usage:
    python simple_agent.py

Requirements:
    pip install groq python-dotenv
"""

import os
import json
from typing import Dict, Any, List
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

# =============================================================================
# TOOLS: Functions the agent can call
# =============================================================================

TOOLS = {
    "search": {
        "description": "Search for information about a topic",
        "function": lambda topic: f"Information about {topic}: [Mock search result]"
    },
    "calculate": {
        "description": "Calculate a math expression",
        "function": lambda expr: str(eval(expr))
    }
}

# =============================================================================
# AGENT CORE
# =============================================================================

class SimpleAgent:
    def __init__(self):
        self.llm = Groq(
            api_key=os.getenv("GROQ_API_KEY")
        )
        # Using GPT OSS 120B model via Groq Cloud
        self.model = "openai/gpt-oss-120b"
        self.memory = []  # Conversation history
        
    def run(self, goal: str, max_iterations: int = 5) -> str:
        """Main agent loop with SPOAR pattern."""
        
        print(f"\n{'='*60}")
        print(f"🎯 GOAL: {goal}")
        print(f"{'='*60}\n")
        
        # Initialize context
        context = {"goal": goal, "iteration": 0}
        
        for iteration in range(1, max_iterations + 1):
            context["iteration"] = iteration
            print(f"\n--- ITERATION {iteration} ---\n")
            
            # 🔍 SENSE: Gather current context
            context = self._sense(context)
            
            # 🧠 PLAN: Decide what to do next
            plan = self._plan(context)
            
            # Check if done
            if plan["action"] == "COMPLETE":
                self._log_phase("✅ COMPLETE", {"answer": plan["answer"]})
                return plan["answer"]
            
            # ⚡ ACT: Execute the planned action
            result = self._act(plan)
            
            # 📊 OBSERVE: Record what happened
            observation = self._observe(plan, result)
            
            # 💭 REFLECT: Evaluate progress
            reflection = self._reflect(context, observation)
            
            # Update context for next iteration
            context["last_action"] = plan
            context["last_result"] = result
            context["last_reflection"] = reflection
        
        return "❌ Max iterations reached without completion"
    
    def _sense(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """SENSE: Gather information about current state."""
        self._log_phase("👁️  SENSE", {
            "iteration": context["iteration"],
            "goal": context["goal"],
            "previous_actions": context.get("last_action", "None")
        })
        
        # Return enriched context
        return {
            **context,
            "available_tools": list(TOOLS.keys()),
            "tool_descriptions": {k: v["description"] for k, v in TOOLS.items()}
        }
    
    def _plan(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """PLAN: Use LLM to decide next action."""
        
        # Build planning prompt
        tools_text = "\n".join([
            f"- {name}: {info['description']}" 
            for name, info in TOOLS.items()
        ])
        
        prompt = f"""Goal: {context['goal']}

Available Tools:
{tools_text}

Previous Action: {context.get('last_action', {}).get('tool', 'None')}
Previous Result: {str(context.get('last_result', 'None'))[:100]}
Previous Reflection: {context.get('last_reflection', 'None')}

Decide what to do next. Respond with ONLY valid JSON:

{{
  "action": "USE_TOOL" or "COMPLETE",
  "tool": "tool_name",
  "args": {{"arg_name": "value"}},
  "reasoning": "why you chose this",
  "answer": "final answer (only if COMPLETE)"
}}

Rules:
- Use USE_TOOL if you need more information
- Use COMPLETE when you can answer the goal
- Only respond with JSON, nothing else"""

        # Call LLM
        response = self.llm.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a planning agent. Always respond with valid JSON only."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3
        )
        
        # Parse response
        plan = self._parse_json(response.choices[0].message.content)
        
        self._log_phase("🧠 PLAN", {
            "action": plan["action"],
            "tool": plan.get("tool", "N/A"),
            "reasoning": plan["reasoning"][:80] + "..."
        })
        
        return plan
    
    def _act(self, plan: Dict[str, Any]) -> Any:
        """ACT: Execute the planned action."""
        
        if plan["action"] != "USE_TOOL":
            return None
        
        tool_name = plan["tool"]
        args = plan.get("args", {})
        
        # Execute tool
        if tool_name not in TOOLS:
            result = f"ERROR: Tool '{tool_name}' not found"
        else:
            try:
                # Call the tool function with arguments
                tool_func = TOOLS[tool_name]["function"]
                result = tool_func(**args)
            except Exception as e:
                result = f"ERROR: {str(e)}"
        
        self._log_phase("⚡ ACT", {
            "tool": tool_name,
            "args": args,
            "result": str(result)[:100]
        })
        
        return result
    
    def _observe(self, plan: Dict[str, Any], result: Any) -> Dict[str, Any]:
        """OBSERVE: Record and analyze what happened."""
        
        observation = {
            "action_taken": plan.get("tool", plan.get("action")),
            "result": result,
            "success": "ERROR" not in str(result)
        }
        
        self._log_phase("📊 OBSERVE", {
            "action": observation["action_taken"],
            "success": observation["success"]
        })
        
        return observation
    
    def _reflect(self, context: Dict[str, Any], observation: Dict[str, Any]) -> str:
        """REFLECT: Evaluate progress toward goal."""
        
        prompt = f"""Goal: {context['goal']}

Action Taken: {observation['action_taken']}
Result: {observation['result']}
Success: {observation['success']}

In 1-2 sentences, reflect on:
1. Did this action help progress toward the goal?
2. What should happen next?

Be brief and actionable."""
        
        response = self.llm.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You reflect on agent progress. Be brief."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=100
        )
        
        reflection = response.choices[0].message.content.strip()
        
        self._log_phase("💭 REFLECT", {"reflection": reflection})
        
        return reflection
    
    def _log_phase(self, phase: str, data: Dict[str, Any]):
        """Simple logging for visibility."""
        print(f"{phase}")
        for key, value in data.items():
            print(f"  {key}: {value}")
        print()
    
    def _parse_json(self, text: str) -> Dict[str, Any]:
        """Parse JSON from LLM response."""
        # Remove markdown code blocks if present
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]
        
        return json.loads(text.strip())

# =============================================================================
# USAGE
# =============================================================================
