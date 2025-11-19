# Spacy Fallback - Quick Reference

## 🚀 Quick Start

```bash
# 1. Install (Python 3.11-3.12 only)
python setup_spacy.py

# 2. Test
python test_spacy_fallback.py

# 3. Use normally - it works automatically!
```

---

## 📋 What It Does

**Extracts names from Public Notes when structured methods fail**

- Uses AI (Spacy NLP) to find person names
- Assigns unit types based on keywords in context
- Works for both GYG and non-GYG bookings

---

## ⚡ When It Activates

### GYG Bookings
```
GYG Standard → Fails
   ↓
GYG MDA → Fails
   ↓
🆕 Spacy Fallback → Tries
```

### Non-GYG Bookings
```
Structured Fields (First + Last Name) → Empty
   ↓
🆕 Spacy Fallback → Tries
```

---

## 🔍 How It Works

1. **Extracts PERSON entities** from public notes using Spacy NER
2. **Looks for keywords** near each name (adult, child, infant, youth)
3. **Assigns unit types** based on keywords or remaining units

---

## 📝 Example

**Input:**
```
Public Notes: "Tour with John Smith (adult) and Tommy Smith (child)"
Units: 1 Adult, 1 Child
```

**Output:**
```
John Smith → Adult (keyword "adult" found)
Tommy Smith → Child (keyword "child" found)
```

---

## 🔑 Keywords Detected

| Unit Type | Keywords |
|-----------|----------|
| **Adult** | adult, adults, parent, guardian, mother, father, mom, dad |
| **Child** | child, children, kid, kids, son, daughter, boy, girl |
| **Infant** | infant, baby, toddler |
| **Youth** | youth, teen, teenager, student |

---

## ⚙️ Requirements

### Python Version
- ✅ Python 3.11 or 3.12
- ❌ Python 3.14+ (not compatible)

### Dependencies
```bash
pip install spacy==3.7.0
python -m spacy download en_core_web_sm
```

---

## 🛠️ Installation

### Automated (Recommended)
```bash
python setup_spacy.py
```

### Manual
```bash
pip install spacy==3.7.0
python -m spacy download en_core_web_sm
```

### Verify
```bash
python test_spacy_fallback.py
```

---

## 🐛 Troubleshooting

### "Spacy not available" Warning
```bash
pip install spacy==3.7.0
```

### "Spacy model not found" Warning
```bash
python -m spacy download en_core_web_sm
```

### Python 3.14 Compatibility Error
**Solution**: Use Python 3.11 or 3.12
```bash
# Create venv with Python 3.12
python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### No Names Extracted
- Check if public notes contain actual person names
- Check if names are in recognizable format
- Review logs for extraction details

---

## 📊 Files Created

| File | Purpose |
|------|---------|
| `extractors/spacy_fallback.py` | Main implementation |
| `setup_spacy.py` | Automated setup script |
| `test_spacy_fallback.py` | Test and demo script |
| `SPACY_FALLBACK_GUIDE.md` | Complete documentation |
| `IMPLEMENTATION_SUMMARY.md` | Implementation overview |
| `QUICK_REFERENCE.md` | This file |

---

## 📖 Documentation

- **Full Guide**: `SPACY_FALLBACK_GUIDE.md`
- **Implementation Details**: `IMPLEMENTATION_SUMMARY.md`
- **General Usage**: `README.md`

---

## ✅ Success Indicators

Look for these log messages:

```
INFO: Spacy fallback successful for ORDER-123: extracted 3 travelers
```

Check output for correctly assigned unit types!

---

## ⚠️ Limitations

- ❌ Cannot extract dates of birth
- ❌ Cannot calculate ages
- ⚠️ Accuracy depends on text quality
- ⚠️ English text only

---

## 🎯 When to Use

Fallback is **automatic** - just use the system normally!

It activates when:
- GYG bookings have no structured names
- Non-GYG bookings have empty name fields
- Public notes contain person names

---

## 💡 Pro Tips

1. **Better public notes = better extraction**
   - Include full names
   - Add keywords (adult, child, etc.)
   - Use clear formatting

2. **Check logs for debugging**
   - Logs show when fallback activates
   - Logs show what names were extracted
   - Logs show unit type assignments

3. **Python version matters**
   - Use 3.11 or 3.12 for best experience
   - 3.14+ won't work with Spacy

---

## 🚨 Emergency Disable

If you need to disable Spacy fallback:

```bash
pip uninstall spacy
```

System will work normally without fallback (standard extractors still work).

---

## 📞 Support

- Check logs: `namesgen.log` or `namesgen_gui.log`
- Read full guide: `SPACY_FALLBACK_GUIDE.md`
- Test setup: `python test_spacy_fallback.py`

---

## ✨ Summary

**Spacy Fallback** = Smart AI-powered name extraction when normal methods fail

- ✅ Automatic
- ✅ Smart unit assignment
- ✅ Handles edge cases
- ✅ Production ready
- ✅ Well documented

**Just install and forget - it works automatically! 🎉**

