from google.colab import output
from IPython.display import HTML, display
import json

# Python global variables
server_racks = []
cooling_systems = []

def create_grid(rows=5, cols=5):
    global server_racks, cooling_systems
    print("Single Click: Server Rack | Double Click: Cooling Unit")

    html_code = f"""
    <div id="grid-root">
        <style>
            .grid-wrapper {{ display: flex; flex-direction: column; gap: 15px; padding: 10px; }}
            .grid-container {{ display: flex; flex-direction: column-reverse; gap: 4px; width: fit-content; }}
            .row {{ display: flex; gap: 4px; }}
            .cell {{
                width: 45px; height: 45px; border: 1px solid #ccc;
                display: flex; align-items: center; justify-content: center;
                cursor: pointer; background: #fff;
                font-size: 16px; font-weight: bold; color: red;
                user-select: none; transition: 0.2s;
            }}
            .cell svg {{ width: 24px; height: 24px; fill: white; }}
            .cell.single-active {{ background: #4CAF50 !important; border-color: #4CAF50; }}
            .cell.double-active {{ background: #2196F3 !important; border-color: #2196F3; }}

            #submit-btn {{ width: 150px; padding: 10px; cursor: pointer; background: #333; color: white; border: none; border-radius: 4px; }}
            #submit-btn:disabled {{ background: #ccc; cursor: not-allowed; opacity: 0.6; }}

            /* Class to lock the grid after submission */
            .locked {{ pointer-events: none; opacity: 0.8; }}
        </style>

        <div class="grid-wrapper">
            <div id="status-msg" style="font-weight: bold; color: #333;"></div>
            <div class="grid-container" id="myGrid"></div>
            <button id="submit-btn" disabled>Submit Selections</button>
        </div>
    </div>
    <script>
        (function() {{
            const rows = {rows}, cols = {cols};
            const singleSelected = new Set();
            const doubleSelected = new Set();
            const grid = document.getElementById('myGrid');
            const submitBtn = document.getElementById('submit-btn');
            const statusMsg = document.getElementById('status-msg');
            let clickTimer = null;

            const ICONS = {{
                server: `<svg viewBox="0 0 24 24"><path d="M20 13H4c-.55 0-1 .45-1 1v4c0 .55.45 1 1 1h16c.55 0 1-.45 1-1v-4c0-.55-.45-1-1-1zM7 17H5v-2h2v2zm13-8H4c-.55 0-1 .45-1 1v4c0 .55.45 1 1 1h16c.55 0 1-.45 1-1v-4c0-.55-.45-1-1-1zM7 13H5v-2h2v2zm13-8H4c-.55 0-1 .45-1 1v4c0 .55.45 1 1 1h16c.55 0 1-.45 1-1V6c0-.55-.45-1-1-1zM7 9H5V7h2v2z"/></svg>`,
                snowflake: `<svg viewBox="0 0 24 24"><path d="M22 11h-4.17l3.24-3.24-1.41-1.42L15 11h-2V9l4.66-4.66-1.42-1.41L13 6.17V2h-2v4.17L7.76 2.93 6.34 4.34 11 9v2H9L4.34 6.34 2.93 7.76 6.17 11H2v2h4.17l-3.24 3.24 1.41 1.42L9 13h2v2l-4.66 4.66 1.42 1.41L11 17.83V22h2v-4.17l3.24 3.24 1.42-1.41L13 15v-2h2l4.66 4.66 1.41-1.42L17.83 13H22v-2z"/></svg>`
            }};

            function updateButtonState() {{
                submitBtn.disabled = (singleSelected.size === 0 && doubleSelected.size === 0);
            }}

            function updateCellContent(cell, r, c, pos) {{
                if (singleSelected.has(pos)) {{
                    cell.innerHTML = ICONS.server;
                    cell.className = 'cell single-active';
                }} else if (doubleSelected.has(pos)) {{
                    cell.innerHTML = ICONS.snowflake;
                    cell.className = 'cell double-active';
                }} else {{
                    cell.innerText = r + ", " + c;
                    cell.className = 'cell';
                }}
            }}

            for (let r = 0; r < rows; r++) {{
                const rowDiv = document.createElement('div');
                rowDiv.className = 'row';
                for (let c = 0; c < cols; c++) {{
                    const cell = document.createElement('div');
                    const pos = JSON.stringify([r, c]);
                    cell.className = 'cell';
                    cell.innerText = r + ", " + c;

                    cell.onclick = () => {{
                        if (clickTimer) clearTimeout(clickTimer);
                        clickTimer = setTimeout(() => {{
                            doubleSelected.delete(pos);
                            if (singleSelected.has(pos)) singleSelected.delete(pos);
                            else singleSelected.add(pos);
                            updateCellContent(cell, r, c, pos);
                            updateButtonState();
                        }}, 250);
                    }};

                    cell.ondblclick = () => {{
                        clearTimeout(clickTimer);
                        singleSelected.delete(pos);
                        if (doubleSelected.has(pos)) doubleSelected.delete(pos);
                        else doubleSelected.add(pos);
                        updateCellContent(cell, r, c, pos);
                        updateButtonState();
                    }};
                    rowDiv.appendChild(cell);
                }}
                grid.appendChild(rowDiv);
            }}

            window.gridPromise = new Promise((resolve) => {{
                submitBtn.onclick = () => {{
                    const payload = {{
                        single: Array.from(singleSelected).map(s => JSON.parse(s)),
                        double: Array.from(doubleSelected).map(s => JSON.parse(s))
                    }};

                    // LOCK THE GRID UI
                    grid.classList.add('locked');
                    submitBtn.style.display = 'none';
                    statusMsg.innerText = "Selection Locked";

                    resolve(payload);
                }};
            }});
        }})();
    </script>
    """
    display(HTML(html_code))

    result = output.eval_js("window.gridPromise")

    server_racks = result['single']
    cooling_systems = result['double']

    print(f"Selection Saved! \nServer Racks ({len(server_racks)}): {server_racks}\nCooling Units ({len(cooling_systems)}): {cooling_systems}")