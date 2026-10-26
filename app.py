            # Maak de HTML string
            html_card = f"""
            <div class="clean-card {item['card_class']}">
                <div style="margin-bottom: 8px;">
                    <span class="prio-pill">{item['priority_label']}</span> <span class="topic-pill">{item['topic_readable']}</span> {item['badge_html']} 
                    <span style="font-size: 13px; color: #475569; font-weight: bold; margin-left: 8px;">#{idx} | 🕒 {item['date_str']} | Bron: {item['source']}</span>
                </div>
                <h4 class="card-title">{item['title_nl']}</h4>
                <div class="card-subtitle">Originele kop: {item['title_orig']}</div>
                {also}
                <div style="font-size: 13px; color: #1e3a8a; font-weight: 600; margin-bottom: 4px;">🎯 Sectoren: {item['sector_str']}</div>
                <div style="margin-bottom: 8px;">{chips}</div>
                <hr>
                <div class="card-text"><strong>🗣️ Wat betekent dit:</strong> {item['jip']}</div>
                <div class="card-text"><strong>📊 Economische impact:</strong> {item['impact']}</div>
                <div style="margin-top: 10px;"><a href="{item['link']}" target="_blank" style="font-weight: bold; color: #1d4ed8; text-decoration: none;">🔗 Lees originele bron</a></div>
            </div>
            """
            
            # CRUCIAAL: Vervang ALLE enters door een spatie. Zo voorkom je elk risico op een Markdown code-blok.
            st.markdown(html_card.replace('\n', ' '), unsafe_allow_html=True)
            export_lines.append(f"## #{idx} [{item['priority_label']}] {item['title_nl']} ({item['date_str']})\n- Impact: {item['impact']}\n- Bron: {item['link']}\n\n")
