import xml.etree.ElementTree as ET
import pandas as pd
from pathlib import Path
import json


def extract_railways_xml(osm_file):
    print(f"Started processing file: {osm_file}")
    print(f"File exists: {Path(osm_file).exists()}")
    print(f"File size: {Path(osm_file).stat().st_size / (1024 * 1024):.2f} MB")

    # 存储所有节点信息
    nodes = {}
    # 存储铁路信息
    railways = []
    # 存储所有铁路节点的详细信息
    railway_points = []

    try:
        # 解析XML文件
        tree = ET.parse(osm_file)
        root = tree.getroot()

        # 首先获取所有节点的经纬度信息
        print("Collecting node coordinates...")
        for node in root.findall('.//node'):
            node_id = node.attrib['id']
            lat = float(node.attrib['lat'])
            lon = float(node.attrib['lon'])
            # 获取节点的标签信息
            tags = {tag.attrib['k']: tag.attrib['v'] for tag in node.findall('tag')}
            nodes[node_id] = {
                'lat': lat,
                'lon': lon,
                'tags': tags
            }
        print(f"Collected {len(nodes)} nodes")

        # 遍历所有way元素
        print("Processing railway ways...")
        for way in root.findall('.//way'):
            # 获取所有tag元素
            tags = {tag.attrib['k']: tag.attrib['v'] for tag in way.findall('tag')}

            # 检查是否为铁路
            if 'railway' in tags:
                way_id = way.attrib['id']
                railway_name = tags.get('name', 'Unknown')
                railway_type = tags.get('railway', '')

                # 获取所有节点引用
                node_refs = [nd.attrib['ref'] for nd in way.findall('nd')]

                # 记录铁路基本信息
                railway_info = {
                    'railway_id': way_id,
                    'name': railway_name,
                    'railway_type': railway_type,
                    'gauge': tags.get('gauge', ''),
                    'electrified': tags.get('electrified', ''),
                    'service': tags.get('service', ''),
                    'usage': tags.get('usage', ''),
                    'node_count': len(node_refs)
                }
                railways.append(railway_info)

                # 记录每个节点的详细信息
                for seq, node_ref in enumerate(node_refs):
                    if node_ref in nodes:
                        node_data = nodes[node_ref]
                        point_info = {
                            'railway_id': way_id,
                            'railway_name': railway_name,
                            'railway_type': railway_type,
                            'node_id': node_ref,
                            'sequence': seq + 1,
                            'lat': node_data['lat'],
                            'lon': node_data['lon'],
                            'is_start': seq == 0,
                            'is_end': seq == len(node_refs) - 1
                        }
                        # 添加节点的标签信息
                        point_info.update(node_data['tags'])
                        railway_points.append(point_info)

        print(f"Successfully processed {len(railways)} railways with {len(railway_points)} points")

        return pd.DataFrame(railways), pd.DataFrame(railway_points)

    except Exception as e:
        print(f"Error during file processing: {str(e)}")
        raise


def main():
    try:
        # OSM文件路径
        osm_file = "E:\\靖神铁路\\jingbian-shenmu.osm"

        # 检查文件是否存在
        if not Path(osm_file).exists():
            print(f"Error: File '{osm_file}' does not exist!")
            return

        # 提取铁路数据
        railways_df, points_df = extract_railways_xml(osm_file)

        # 保存铁路基本信息
        railways_df.to_csv('railways2.csv', index=False, encoding='utf-8')
        print(f"\nRailway information saved to railways.csv")

        # 保存所有节点信息
        points_df.to_csv('railway_points.csv', index=False, encoding='utf-8')
        print(f"Railway points saved to railway_points.csv")

        # 打印基本统计信息
        print("\nRailway statistics:")
        print(f"Total railways: {len(railways_df)}")
        print(f"Total points: {len(points_df)}")
        print("\nRailway types distribution:")
        print(railways_df['railway_type'].value_counts())

        # 打印经纬度范围
        print("\nGeographic extent:")
        print(f"Latitude range: {points_df['lat'].min():.6f} to {points_df['lat'].max():.6f}")
        print(f"Longitude range: {points_df['lon'].min():.6f} to {points_df['lon'].max():.6f}")

        # 为每条铁路生成GeoJSON格式的坐标数据
        geojson_features = []
        for railway_id in railways_df['railway_id']:
            railway_points = points_df[points_df['railway_id'] == railway_id]
            railway_info = railways_df[railways_df['railway_id'] == railway_id].iloc[0]

            coordinates = railway_points[['lon', 'lat']].values.tolist()

            feature = {
                "type": "Feature",
                "geometry": {
                    "type": "LineString",
                    "coordinates": coordinates
                },
                "properties": {
                    "railway_id": railway_id,
                    "name": railway_info['name'],
                    "railway_type": railway_info['railway_type']
                }
            }
            geojson_features.append(feature)

        geojson = {
            "type": "FeatureCollection",
            "features": geojson_features
        }

        # 保存GeoJSON文件
        with open('railways.geojson', 'w', encoding='utf-8') as f:
            json.dump(geojson, f, ensure_ascii=False, indent=2)
        print(f"GeoJSON data saved to railways.geojson")

    except Exception as e:
        print(f"Error processing OSM file: {str(e)}")
        print("Detailed error information:")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()