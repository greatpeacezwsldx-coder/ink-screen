// DatabaseHelper.ets - 数据库管理器
import relationalStore from '@ohos.data.relationalStore';
import common from '@ohos.app.ability.common';
import { BusinessError } from '@kit.BasicServicesKit';

const DATABASE_NAME = 'PhotoAlbum.db';
const DATABASE_VERSION = 1;

// 表名常量
export interface TableNamesInterface {
  readonly PHOTOS: string;
  readonly MEMORIES: string;
  readonly SETTINGS: string;
}
export const TableNames: TableNamesInterface = {
  PHOTOS: 'photos',
  MEMORIES: 'memories',
  SETTINGS: 'settings'
};

// 创建表的SQL语句
const CREATE_PHOTOS_TABLE = `
  CREATE TABLE IF NOT EXISTS photos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uri TEXT NOT NULL,
    create_time INTEGER NOT NULL,
    modify_time INTEGER NOT NULL,
    year INTEGER NOT NULL,
    month INTEGER NOT NULL,
    day INTEGER NOT NULL,
    is_year_memory INTEGER DEFAULT 0,
    is_selected INTEGER DEFAULT 0,
    score INTEGER DEFAULT 0
  )
`;

const CREATE_MEMORIES_TABLE = `
  CREATE TABLE IF NOT EXISTS memories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    year INTEGER NOT NULL,
    month INTEGER NOT NULL,
    day INTEGER NOT NULL,
    photo_id INTEGER,
    create_time INTEGER NOT NULL,
    description TEXT,
    FOREIGN KEY (photo_id) REFERENCES photos(id)
  )
`;

const CREATE_SETTINGS_TABLE = `
  CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    update_time INTEGER NOT NULL
  )
`;

// 照片数据结构
export interface PhotoData {
  id?: number;
  uri: string;
  create_time: number;
  modify_time: number;
  year: number;
  month: number;
  day: number;
  is_year_memory?: number;
  is_selected?: number;
  score?: number;
}

// 回忆数据结构
export interface MemoryData {
  id?: number;
  year: number;
  month: number;
  day: number;
  photo_id?: number;
  create_time: number;
  description?: string;
}

class DatabaseHelper {
  private rdbStore: relationalStore.RdbStore | null = null;
  private context: common.UIAbilityContext | null = null;

  // 初始化数据库
  async init(context: common.UIAbilityContext): Promise<boolean> {
    return new Promise((resolve) => {
      try {
        this.context = context;

        const config: relationalStore.StoreConfig = {
          name: DATABASE_NAME,
          securityLevel: relationalStore.SecurityLevel.S1
        };

        console.info('开始初始化数据库...');
        
        // 使用回调方式初始化数据库
        relationalStore.getRdbStore(context, config, (err: BusinessError, store: relationalStore.RdbStore) => {
          if (err) {
            console.error(`数据库初始化失败: ${err.code}, ${err.message}`);
            resolve(false);
            return;
          }
          
          console.info('数据库连接成功');
          this.rdbStore = store;

          // 创建表
          try {
            this.createTablesSync();
            console.info('数据库表创建成功');
            console.info('数据库初始化成功');
            resolve(true);
          } catch (tableError) {
            console.error(`创建表失败: ${JSON.stringify(tableError)}`);
            resolve(false);
          }
        });
      } catch (error) {
        console.error(`数据库初始化异常: ${JSON.stringify(error)}`);
        resolve(false);
      }
    });
  }

  // 同步创建表
  private createTablesSync(): void {
    if (!this.rdbStore) {
      throw new Error('数据库未初始化');
    }

    // 创建照片表
    this.rdbStore.executeSql(CREATE_PHOTOS_TABLE);
    console.info('照片表创建完成');

    // 创建回忆表
    this.rdbStore.executeSql(CREATE_MEMORIES_TABLE);
    console.info('回忆表创建完成');

    // 创建设置表
    this.rdbStore.executeSql(CREATE_SETTINGS_TABLE);
    console.info('设置表创建完成');
  }

  // 检查数据库是否已初始化
  isInitialized(): boolean {
    return this.rdbStore !== null;
  }

  // 创建数据表
  private async createTables(): Promise<void> {
    if (!this.rdbStore) {
      throw new Error('数据库未初始化');
    }

    // 创建照片表
    await this.rdbStore.executeSql(CREATE_PHOTOS_TABLE);

    // 创建回忆表
    await this.rdbStore.executeSql(CREATE_MEMORIES_TABLE);

    // 创建设置表
    await this.rdbStore.executeSql(CREATE_SETTINGS_TABLE);
  }

  // 获取数据库实例
  getStore(): relationalStore.RdbStore | null {
    return this.rdbStore;
  }

  // 插入照片
  async insertPhoto(photo: PhotoData): Promise<number> {
    if (!this.rdbStore) {
      throw new Error('数据库未初始化');
    }

    const valueBucket: relationalStore.ValuesBucket = {
      uri: photo.uri,
      create_time: photo.create_time,
      modify_time: photo.modify_time,
      year: photo.year,
      month: photo.month,
      day: photo.day,
      is_year_memory: photo.is_year_memory || 0,
      is_selected: photo.is_selected || 0,
      score: photo.score || 0
    };

    const result = await this.rdbStore.insert(TableNames.PHOTOS, valueBucket);
    console.info(`照片插入成功，ID: ${result}`);
    return result;
  }

  // 批量插入照片
  async batchInsertPhotos(photos: Array<PhotoData>): Promise<void> {
    if (!this.rdbStore) {
      throw new Error('数据库未初始化');
    }

    for (const photo of photos) {
      await this.insertPhoto(photo);
    }
  }

  // 查询所有照片
  async queryAllPhotos(): Promise<Array<PhotoData>> {
    if (!this.rdbStore) {
      throw new Error('数据库未初始化');
    }

    const predicates = new relationalStore.RdbPredicates(TableNames.PHOTOS);
    const resultSet = await this.rdbStore.query(predicates, [
      'id', 'uri', 'create_time', 'modify_time', 'year', 'month', 'day',
      'is_year_memory', 'is_selected', 'score'
    ]);

    const photos: Array<PhotoData> = [];
    while (resultSet.goToNextRow()) {
      photos.push({
        id: resultSet.getLong(resultSet.getColumnIndex('id')),
        uri: resultSet.getString(resultSet.getColumnIndex('uri')),
        create_time: resultSet.getLong(resultSet.getColumnIndex('create_time')),
        modify_time: resultSet.getLong(resultSet.getColumnIndex('modify_time')),
        year: resultSet.getLong(resultSet.getColumnIndex('year')),
        month: resultSet.getLong(resultSet.getColumnIndex('month')),
        day: resultSet.getLong(resultSet.getColumnIndex('day')),
        is_year_memory: resultSet.getLong(resultSet.getColumnIndex('is_year_memory')),
        is_selected: resultSet.getLong(resultSet.getColumnIndex('is_selected')),
        score: resultSet.getLong(resultSet.getColumnIndex('score'))
      });
    }
    resultSet.close();

    return photos;
  }

  // 查询往年今日的照片
  async queryYearMemoryPhotos(year: number, month: number, day: number): Promise<Array<PhotoData>> {
    if (!this.rdbStore) {
      throw new Error('数据库未初始化');
    }

    console.info(`查询往年今日照片: year=${year}, month=${month}, day=${day}`);

    // 先尝试查询所有同年同月同日的照片（不限制is_year_memory）
    const predicates = new relationalStore.RdbPredicates(TableNames.PHOTOS)
      .equalTo('year', year)
      .equalTo('month', month)
      .equalTo('day', day);

    const resultSet = await this.rdbStore.query(predicates, [
      'id', 'uri', 'create_time', 'modify_time', 'year', 'month', 'day',
      'is_year_memory', 'is_selected', 'score'
    ]);

    console.info('查询结果集获取成功');

    const photos: Array<PhotoData> = [];
    while (resultSet.goToNextRow()) {
      photos.push({
        id: resultSet.getLong(resultSet.getColumnIndex('id')),
        uri: resultSet.getString(resultSet.getColumnIndex('uri')),
        create_time: resultSet.getLong(resultSet.getColumnIndex('create_time')),
        modify_time: resultSet.getLong(resultSet.getColumnIndex('modify_time')),
        year: resultSet.getLong(resultSet.getColumnIndex('year')),
        month: resultSet.getLong(resultSet.getColumnIndex('month')),
        day: resultSet.getLong(resultSet.getColumnIndex('day')),
        is_year_memory: resultSet.getLong(resultSet.getColumnIndex('is_year_memory')),
        is_selected: resultSet.getLong(resultSet.getColumnIndex('is_selected')),
        score: resultSet.getLong(resultSet.getColumnIndex('score'))
      });
    }
    resultSet.close();

    return photos;
  }

  // 查询已选照片
  async querySelectedPhotos(): Promise<Array<PhotoData>> {
    if (!this.rdbStore) {
      throw new Error('数据库未初始化');
    }

    const predicates = new relationalStore.RdbPredicates(TableNames.PHOTOS)
      .equalTo('is_selected', 1);

    const resultSet = await this.rdbStore.query(predicates, [
      'id', 'uri', 'create_time', 'modify_time', 'year', 'month', 'day',
      'is_year_memory', 'is_selected', 'score'
    ]);

    const photos: Array<PhotoData> = [];
    while (resultSet.goToNextRow()) {
      photos.push({
        id: resultSet.getLong(resultSet.getColumnIndex('id')),
        uri: resultSet.getString(resultSet.getColumnIndex('uri')),
        create_time: resultSet.getLong(resultSet.getColumnIndex('create_time')),
        modify_time: resultSet.getLong(resultSet.getColumnIndex('modify_time')),
        year: resultSet.getLong(resultSet.getColumnIndex('year')),
        month: resultSet.getLong(resultSet.getColumnIndex('month')),
        day: resultSet.getLong(resultSet.getColumnIndex('day')),
        is_year_memory: resultSet.getLong(resultSet.getColumnIndex('is_year_memory')),
        is_selected: resultSet.getLong(resultSet.getColumnIndex('is_selected')),
        score: resultSet.getLong(resultSet.getColumnIndex('score'))
      });
    }
    resultSet.close();

    return photos;
  }

  // 查询最新回忆照片
  async queryLatestMemory(): Promise<PhotoData | null> {
    if (!this.rdbStore) {
      throw new Error('数据库未初始化');
    }

    const predicates = new relationalStore.RdbPredicates(TableNames.PHOTOS)
      .orderByDesc('create_time')
      .limitAs(1);

    const resultSet = await this.rdbStore.query(predicates, [
      'id', 'uri', 'create_time', 'modify_time', 'year', 'month', 'day',
      'is_year_memory', 'is_selected', 'score'
    ]);

    if (resultSet.goToFirstRow()) {
      const photo: PhotoData = {
        id: resultSet.getLong(resultSet.getColumnIndex('id')),
        uri: resultSet.getString(resultSet.getColumnIndex('uri')),
        create_time: resultSet.getLong(resultSet.getColumnIndex('create_time')),
        modify_time: resultSet.getLong(resultSet.getColumnIndex('modify_time')),
        year: resultSet.getLong(resultSet.getColumnIndex('year')),
        month: resultSet.getLong(resultSet.getColumnIndex('month')),
        day: resultSet.getLong(resultSet.getColumnIndex('day')),
        is_year_memory: resultSet.getLong(resultSet.getColumnIndex('is_year_memory')),
        is_selected: resultSet.getLong(resultSet.getColumnIndex('is_selected')),
        score: resultSet.getLong(resultSet.getColumnIndex('score'))
      };
      resultSet.close();
      return photo;
    }

    resultSet.close();
    return null;
  }

  // 更新照片
  async updatePhoto(id: number, updates: Partial<PhotoData>): Promise<void> {
    if (!this.rdbStore) {
      throw new Error('数据库未初始化');
    }

    const valueBucket: relationalStore.ValuesBucket = {};
    if (updates.uri !== undefined) valueBucket.uri = updates.uri;
    if (updates.modify_time !== undefined) valueBucket.modify_time = updates.modify_time;
    if (updates.is_year_memory !== undefined) valueBucket.is_year_memory = updates.is_year_memory;
    if (updates.is_selected !== undefined) valueBucket.is_selected = updates.is_selected;
    if (updates.score !== undefined) valueBucket.score = updates.score;

    const predicates = new relationalStore.RdbPredicates(TableNames.PHOTOS)
      .equalTo('id', id);

    await this.rdbStore.update(valueBucket, predicates);
    console.info(`照片 ${id} 更新成功`);
  }

  // 删除照片
  async deletePhoto(id: number): Promise<void> {
    if (!this.rdbStore) {
      throw new Error('数据库未初始化');
    }

    const predicates = new relationalStore.RdbPredicates(TableNames.PHOTOS)
      .equalTo('id', id);

    await this.rdbStore.delete(predicates);
    console.info(`照片 ${id} 删除成功`);
  }

  // 保存设置
  async saveSetting(key: string, value: string): Promise<void> {
    if (!this.rdbStore) {
      throw new Error('数据库未初始化');
    }

    const valueBucket: relationalStore.ValuesBucket = {
      key: key,
      value: value,
      update_time: Date.now()
    };

    // 使用 replace 模式插入或更新
    await this.rdbStore.insert(TableNames.SETTINGS, valueBucket,
      relationalStore.ConflictResolution.ON_CONFLICT_REPLACE);
  }

  // 获取设置
  async getSetting(key: string): Promise<string | null> {
    if (!this.rdbStore) {
      throw new Error('数据库未初始化');
    }

    const predicates = new relationalStore.RdbPredicates(TableNames.SETTINGS)
      .equalTo('key', key);

    const resultSet = await this.rdbStore.query(predicates, ['value']);

    if (resultSet.goToFirstRow()) {
      const value = resultSet.getString(resultSet.getColumnIndex('value'));
      resultSet.close();
      return value;
    }

    resultSet.close();
    return null;
  }

  // 插入回忆
  async insertMemory(memory: MemoryData): Promise<number> {
    if (!this.rdbStore) {
      throw new Error('数据库未初始化');
    }

    const valueBucket: relationalStore.ValuesBucket = {
      year: memory.year,
      month: memory.month,
      day: memory.day,
      photo_id: memory.photo_id || null,
      create_time: memory.create_time,
      description: memory.description || ''
    };

    const result = await this.rdbStore.insert(TableNames.MEMORIES, valueBucket);
    console.info(`回忆插入成功，ID: ${result}`);
    return result;
  }

  // 查询某一天的回忆
  async queryMemories(year: number, month: number, day: number): Promise<Array<MemoryData>> {
    if (!this.rdbStore) {
      throw new Error('数据库未初始化');
    }

    const predicates = new relationalStore.RdbPredicates(TableNames.MEMORIES)
      .equalTo('year', year)
      .equalTo('month', month)
      .equalTo('day', day);

    const resultSet = await this.rdbStore.query(predicates, [
      'id', 'year', 'month', 'day', 'photo_id', 'create_time', 'description'
    ]);

    const memories: Array<MemoryData> = [];
    while (resultSet.goToNextRow()) {
      memories.push({
        id: resultSet.getLong(resultSet.getColumnIndex('id')),
        year: resultSet.getLong(resultSet.getColumnIndex('year')),
        month: resultSet.getLong(resultSet.getColumnIndex('month')),
        day: resultSet.getLong(resultSet.getColumnIndex('day')),
        photo_id: resultSet.getLong(resultSet.getColumnIndex('photo_id')),
        create_time: resultSet.getLong(resultSet.getColumnIndex('create_time')),
        description: resultSet.getString(resultSet.getColumnIndex('description'))
      });
    }
    resultSet.close();

    return memories;
  }

  // 获取照片数量
  async getPhotoCount(): Promise<number> {
    if (!this.rdbStore) {
      throw new Error('数据库未初始化');
    }

    const predicates = new relationalStore.RdbPredicates(TableNames.PHOTOS);
    const resultSet = await this.rdbStore.query(predicates, ['count(*) as count']);

    if (resultSet.goToFirstRow()) {
      const count = resultSet.getLong(0);
      resultSet.close();
      return count;
    }

    resultSet.close();
    return 0;
  }
}

// 导出单例
export const databaseHelper = new DatabaseHelper();
