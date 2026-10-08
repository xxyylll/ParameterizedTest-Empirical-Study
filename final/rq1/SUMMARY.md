# RQ1 New Analysis Summary

## 数据集
- **merged_data.csv**: 218个Apache项目（SSK数据）
- PT使用情况: 117个项目使用PT (53.7%)

---

## 关键发现

### 1. Retired vs Active Projects 🔥

**Retired项目显著降低PT采用率但不影响使用强度**

| 指标 | Retired (42项目) | Active (176项目) | 统计显著性 |
|------|-----------------|-----------------|-----------|
| **PT Adoption Rate** | 21.4% (9/42) | 61.4% (108/176) | χ²=20.17, p<0.0001*** |
| **PT Intensity (Mean)** | 3.56% | 5.15% | Mann-Whitney U: p=0.66 (ns) |
| **PT Intensity (Median)** | 1.56% | 2.16% | - |

**结论**: Retired项目采用PT的几率显著降低（差异40个百分点），但一旦采用后使用强度与active项目无显著差异。

---

### 2. Project Scale vs PT Adoption (Binary) 📊

**大型项目显著更倾向于采用PT**

#### Java Files (项目规模)
| 规模 | 采用率 | 项目数 |
|------|-------|--------|
| Small | 39.7% | 73 |
| Medium | 50.0% | 72 |
| Large | **71.2%** | 73 |

**χ² = 15.15, p = 0.0005*** → 高度显著**

#### Total Tests (测试规模)
| 规模 | 采用率 | 项目数 |
|------|-------|--------|
| Small | 26.0% | 73 |
| Medium | 55.6% | 72 |
| Large | **79.5%** | 73 |

**χ² = 42.05, p < 0.0001*** → 极度显著**

#### Project Age (项目年龄)
| 年龄段 | 采用率 | 项目数 |
|--------|-------|--------|
| Young (<12) | 65.0% | 40 |
| Medium (12-18) | 49.4% | 81 |
| Old (>18) | 52.6% | 97 |

**χ² = 2.71, p = 0.26 → 不显著**

**结论**: 项目规模（代码量和测试量）是PT采用的强预测因子，年龄不影响采用决策。

---

### 3. Project Characteristics vs PT Intensity (Continuous) 📈

**在已采用PT的项目中，使用强度与项目规模无关**

分析样本: 117个使用PT的项目

| 特征 | Pearson r | p-value | 显著性 |
|------|-----------|---------|--------|
| **files_java** | -0.114 | 0.22 | ns |
| **total_tests** | -0.067 | 0.48 | ns |
| **age** | -0.199 | 0.032* | * |

**结论**: 
- 代码量和测试量与PT使用强度无相关
- 年龄弱负相关（老项目PT使用比例稍低）
- 与Adoption分析形成对比：规模影响"是否采用"，不影响"用多少"

---

### 4. Domain (Category) Effects 🏷️

**方法改进**: 先对比retired vs non-retired，然后仅对active项目进行logistic regression

#### Top Categories (Active项目，176个)

| Category | 项目数 | PT采用率 | PT强度 |
|----------|--------|---------|--------|
| database | 20 | **75.0%** | 6.24% |
| network-client | 17 | **82.4%** | 3.64% |
| library | 75 | 60.0% | 4.02% |
| big-data | 39 | 66.7% | 3.89% |
| build-management | 8 | 62.5% | 1.11% |

#### Logistic Regression (仅Active项目)
- **big-data**: OR = 2.568 (p=0.019*) → big-data项目采用PT几率增加2.57倍
- **retired已排除**: 不参与category分析，避免污染数据

**结论**: 在active项目中，big-data领域显著提高PT采用几率。

---

## 两个核心问题的区别

### Q1: 什么影响PT **采用决策**? (Binary Outcome)
- ✅ **项目规模**: 大型项目显著更倾向采用
- ✅ **测试规模**: 测试多的项目显著更倾向采用  
- ✅ **Retired状态**: Retired项目采用率仅21.4%
- ✅ **Domain**: big-data领域更倾向采用
- ❌ **项目年龄**: 无显著影响

### Q2: 什么影响PT **使用强度**? (Continuous Outcome)
- ❌ **项目规模**: 无相关
- ❌ **测试规模**: 无相关
- ⚠️ **项目年龄**: 弱负相关（r=-0.199, p=0.032*）
- ❌ **Retired状态**: 无显著影响

---

## 方法论改进

### 1. Retired项目单独分析
**旧方法**: Retired和Active项目混在一起分析category效应  
**新方法**: 
1. 先对比retired vs active的adoption和intensity
2. 仅对active项目进行logistic regression
3. 避免retired项目（低采用率）污染category分析

### 2. 区分Adoption vs Intensity
**旧方法**: 混淆"采用与否"和"使用程度"  
**新方法**: 
- Adoption (binary): Chi-square, Logistic regression
- Intensity (continuous): Pearson correlation, Mann-Whitney U

### 3. 可视化改进
**旧方法**: Scatter plots不够直观  
**新方法**: Violin plots清晰展示分布差异

---

## 文件清单

### Scripts
- `pt_adoption_vs_characteristics_ssk.py`: 采用率分析（Chi-square）
- `pt_correlation_analysis_ssk.py`: 使用强度相关性（Pearson）
- `category_pt_adoption_analysis.py`: 领域分析（Retired对比 + Logistic回归）

### Outputs
- 6个CSV文件（详细统计结果）
- 6个PNG图片（可视化）

---

*Data: 218 Apache projects from SSK dataset*  
*Analysis Date: 2026-06-08*
