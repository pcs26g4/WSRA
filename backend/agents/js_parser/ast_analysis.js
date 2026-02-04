const parser = require("@babel/parser");
const traverse = require("@babel/traverse").default;
const generate = require("@babel/generator").default; // Optional if we need code generation
const fs = require("fs");

// Read code from stdin
const code = fs.readFileSync(0, "utf8");

const sources = [];
const sinks = [];
const vulnerabilities = [];

// Configuration for Sources and Sinks
const SOURCE_PATTERNS = [
  "location.search", "location.hash", "location.href",
  "document.cookie", "document.referrer",
  "URLSearchParams", // Usually followed by .get()
  "localStorage", "sessionStorage",
  "postMessage" // Event data
];

const SINK_PATTERNS = [
  { name: "innerHTML", risk: "high", type: "DOM_XSS" },
  { name: "outerHTML", risk: "high", type: "DOM_XSS" },
  { name: "document.write", risk: "high", type: "DOM_XSS" },
  { name: "eval", risk: "critical", type: "CODE_INJECTION" },
  { name: "setTimeout", risk: "medium", type: "CODE_INJECTION" },
  { name: "setInterval", risk: "medium", type: "CODE_INJECTION" },
  { name: "Function", risk: "high", type: "CODE_INJECTION" },
  { name: "location.assign", risk: "medium", type: "OPEN_REDIRECT" },
  { name: "location.replace", risk: "medium", type: "OPEN_REDIRECT" },
  { name: "window.open", risk: "medium", type: "OPEN_REDIRECT" },
  { name: "fetch", risk: "low", type: "SSRF" }, // Context dependent
];

try {
  const ast = parser.parse(code, {
    sourceType: "unambiguous",
    plugins: ["jsx", "typescript"],
  });

  traverse(ast, {
    // 1. Detect Sources (Assignments or Variable Declarations)
    // e.g., const q = location.search;
    VariableDeclarator(path) {
      if (path.node.init) {
        checkSource(path.node.init, path.node.loc?.start?.line);
      }
    },
    AssignmentExpression(path) {
      // e.g., q = location.search;
      checkSource(path.node.right, path.node.loc?.start?.line);
    },
    
    // 2. Detect Sinks (Assignments or Call Expressions)
    // e.g., element.innerHTML = q;
    AssignmentExpression(path) {
      // Check for property assignment sinks (innerHTML, etc.)
      if (path.node.left.type === "MemberExpression") {
        const propertyName = path.node.left.property.name;
        const match = SINK_PATTERNS.find(s => s.name === propertyName);
        if (match) {
           // We found a sink!
           sinks.push({
             name: match.name,
             line: path.node.loc?.start?.line,
             type: match.type,
             risk: match.risk
           });
        }
      }
    },
    CallExpression(path) {
      // Check for function call sinks (eval, setTimeout, etc.)
      let calleeName = "";
      
      if (path.node.callee.type === "Identifier") {
        calleeName = path.node.callee.name;
      } else if (path.node.callee.type === "MemberExpression") {
        // e.g. location.assign() or window.eval()
        // We simplify by just checking the property name matching our list or full match string
        // For robustness, let's grab the Code string of the callee
        try {
            // Very basic reconstruction, or just check property
            if (path.node.callee.property && path.node.callee.property.type === "Identifier") {
                const prop = path.node.callee.property.name;
                const obj = path.node.callee.object.name; // might be undefined if complex
                
                if (obj) {
                    calleeName = `${obj}.${prop}`;
                } else {
                    calleeName = prop; // Fallback
                }
            }
        } catch(e) {}
      }

      // Check if this callee matches a sink
      const match = SINK_PATTERNS.find(s => 
          s.name === calleeName || 
          (s.name.includes(".") && calleeName.endsWith(s.name)) ||    // e.g. location.assign
          (!s.name.includes(".") && calleeName === s.name)            // e.g. eval
      );

      if (match) {
        sinks.push({
          name: match.name,
          line: path.node.loc?.start?.line,
          type: match.type,
          risk: match.risk
        });
      }
      
      // Special Source Check: URLSearchParams.get()
      if (calleeName.includes("URLSearchParams") || (path.node.callee.property?.name === "get")) {
          // This is a weak heuristic, assuming .get() on a param object
          // Better: check if object is URLSearchParams
          // For now, let's just log it if we see explicit usage
          // We handle this in member expression check mostly
      }
    },
    
    MemberExpression(path) {
        // Catch direct access like location.search in an expression
        // This runs for every member expression
        checkSource(path.node, path.node.loc?.start?.line);
    }
  });
  
  // Helper to check if a node represents a source
  function checkSource(node, line) {
      if (!node) return;
      
      let codeSnippet = "";
      try {
          // Flatten node to string roughly to check against patterns
          if (node.type === "MemberExpression") {
              const obj = node.object.name || (node.object.type === "ThisExpression" ? "this" : "");
              const prop = node.property.name;
              codeSnippet = `${obj}.${prop}`;
          } else if (node.type === "Identifier") {
             // raw identifier source? unlikely unless passed in
             return; 
          }
      } catch(e) {}

      if (!codeSnippet) return;

      const match = SOURCE_PATTERNS.find(p => codeSnippet.includes(p));
      if (match) {
          // Avoid duplicates on same line
          const exists = sources.find(s => s.name === match && s.line === line);
          if (!exists) {
              sources.push({
                  name: match,
                  line: line
              });
          }
      }
  }

  console.log(JSON.stringify({ sources, sinks, vulnerabilities }));

} catch (e) {
  console.log(JSON.stringify({ error: e.message, stack: e.stack }));
}
